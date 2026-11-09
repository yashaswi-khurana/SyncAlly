import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const SCREENSHOT_DIR = '/home/yashaswi/.gemini/antigravity/brain/dc9c2b1a-d602-472a-8039-5fff377eff3d/scratch/screenshots';
const TARGET_URL = 'https://syncally-frontend.onrender.com/';

const BUYER = {
  email: 'shivanshgaur2p+buyer@gmail.com',
  password: 'kyarakhopass'
};

const SELLER = {
  email: 'shivanshgaur2p+seller@gmail.com',
  password: 'kyarakhopass'
};

async function runDeepAudit() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const findings = {
    buyer: {
      dealsPage: {},
      dealDetail: {},
      marketplace: {},
      newDeal: {},
      orgSettings: {},
      mobileBugs: []
    },
    seller: {
      dealsPage: {},
      dealDetail: {},
      differences: []
    },
    consoleErrors: [],
    networkErrors: []
  };

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      findings.consoleErrors.push({ type: msg.type(), text: msg.text(), location: msg.location() });
    }
  });

  page.on('response', res => {
    if (res.status() >= 400) {
      findings.networkErrors.push({ status: res.status(), url: res.url() });
    }
  });

  // --- BUYER AUDIT ---
  console.log('Logging in as BUYER...');
  await page.goto(TARGET_URL, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', BUYER.email);
  await page.fill('input[type="password"]', BUYER.password);
  await page.click('button:has-text("Enter workspace")');
  await page.waitForTimeout(2500);

  // 1. Deals List
  console.log('Inspecting Deals page...');
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_01_deals.png'), fullPage: true });

  // 2. Open First Deal
  const openDealBtns = await page.$$('button:has-text("Open deal")');
  console.log(`Found ${openDealBtns.length} deal buttons`);
  if (openDealBtns.length > 0) {
    await openDealBtns[0].click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_02_deal_detail.png'), fullPage: true });

    // Inspect Deal Detail structure
    const dealDetailInfo = await page.evaluate(() => {
      const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(h => ({
        tag: h.tagName,
        text: h.textContent?.trim()
      }));
      const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent?.trim(),
        disabled: b.disabled,
        className: b.className
      }));
      const sections = Array.from(document.querySelectorAll('section, [role="tabpanel"], .deal-panel')).map(s => ({
        id: s.id,
        className: s.className,
        title: s.querySelector('h2, h3')?.textContent?.trim()
      }));
      return { headings, buttons, sections, url: window.location.href };
    });
    findings.buyer.dealDetail = dealDetailInfo;
    console.log('Deal detail URL:', dealDetailInfo.url);
    console.log('Deal headings:', dealDetailInfo.headings);

    // Test mobile at Deal Detail
    for (const w of [768, 390, 360]) {
      await page.setViewportSize({ width: w, height: 800 });
      await page.waitForTimeout(500);
      const overflow = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
      }));
      if (overflow.hasOverflow) {
        findings.buyer.mobileBugs.push({ page: 'DealDetail', width: w, ...overflow });
        console.log(`[MOBILE OVERFLOW] Deal Detail at ${w}px: scrollWidth = ${overflow.scrollWidth}`);
      }
      if (w === 390) {
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_deal_mobile_390.png'), fullPage: true });
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });

    // Let's test tabs / sections if any
    const actionBtns = await page.$$('button');
    console.log(`Checking interactions on Deal Detail...`);
  }

  // 3. Test Marketplace
  console.log('Testing Marketplace...');
  const mktBtn = await page.$('button:has-text("Marketplace"), a:has-text("Marketplace")');
  if (mktBtn) {
    await mktBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_03_marketplace.png'), fullPage: true });
    findings.buyer.marketplace = await page.evaluate(() => ({
      title: document.title,
      headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent?.trim()),
      cards: document.querySelectorAll('.marketplace-card, article, tr').length
    }));
  }

  // 4. Test New Deal
  console.log('Testing New Deal...');
  const newDealBtn = await page.$('button:has-text("New deal"), a:has-text("New deal")');
  if (newDealBtn) {
    await newDealBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_04_new_deal.png'), fullPage: true });
    findings.buyer.newDeal = await page.evaluate(() => ({
      inputs: Array.from(document.querySelectorAll('input, select, textarea')).map(i => ({
        type: i.getAttribute('type') || i.tagName,
        name: i.getAttribute('name'),
        id: i.id,
        placeholder: i.getAttribute('placeholder')
      }))
    }));
  }

  // 5. Test Organizations / Settings
  console.log('Testing Organizations...');
  const orgBtn = await page.$('button:has-text("Organizations"), a:has-text("Organizations")');
  if (orgBtn) {
    await orgBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_05_organizations.png'), fullPage: true });
    findings.buyer.orgSettings = await page.evaluate(() => ({
      headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent?.trim())
    }));
  }

  // Sign out buyer
  console.log('Signing out Buyer...');
  const signOutBtn = await page.$('button:has-text("Sign out")');
  if (signOutBtn) {
    await signOutBtn.click();
    await page.waitForTimeout(1500);
  }

  // --- SELLER AUDIT ---
  console.log('Logging in as SELLER...');
  await page.fill('input[type="email"]', SELLER.email);
  await page.fill('input[type="password"]', SELLER.password);
  await page.click('button:has-text("Enter workspace")');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'seller_01_deals.png'), fullPage: true });

  const sellerOpenBtns = await page.$$('button:has-text("Open deal")');
  console.log(`Seller found ${sellerOpenBtns.length} deal buttons`);
  if (sellerOpenBtns.length > 0) {
    await sellerOpenBtns[0].click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'seller_02_deal_detail.png'), fullPage: true });
    findings.seller.dealDetail = await page.evaluate(() => ({
      headings: Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(h => ({
        tag: h.tagName,
        text: h.textContent?.trim()
      })),
      buttons: Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent?.trim(),
        disabled: b.disabled
      }))
    }));
  }

  fs.writeFileSync(
    '/home/yashaswi/.gemini/antigravity/brain/dc9c2b1a-d602-472a-8039-5fff377eff3d/scratch/deep_audit_report.json',
    JSON.stringify(findings, null, 2)
  );

  await browser.close();
  console.log('Deep audit complete!');
}

runDeepAudit().catch(err => {
  console.error('Deep audit failed:', err);
  process.exit(1);
});
