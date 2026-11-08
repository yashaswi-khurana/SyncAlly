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

async function audit() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const report = {
    consoleLogs: [],
    networkErrors: [],
    overflowIssues: [],
    testedPages: [],
    buyerAudit: {},
    sellerAudit: {},
    generalFindings: []
  };

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  const page = await context.newPage();

  page.on('console', msg => {
    const text = msg.text();
    report.consoleLogs.push({ type: msg.type(), text });
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`[BROWSER ${msg.type().toUpperCase()}]`, text);
    }
  });

  page.on('pageerror', err => {
    console.log('[PAGE ERROR]', err.message);
    report.consoleLogs.push({ type: 'pageerror', text: err.message, stack: err.stack });
  });

  page.on('requestfailed', req => {
    console.log('[REQUEST FAILED]', req.method(), req.url(), req.failure()?.errorText);
    report.networkErrors.push({
      method: req.method(),
      url: req.url(),
      error: req.failure()?.errorText
    });
  });

  page.on('response', res => {
    if (res.status() >= 400) {
      console.log(`[HTTP ${res.status()}]`, res.url());
      report.networkErrors.push({
        status: res.status(),
        url: res.url()
      });
    }
  });

  console.log('--- 1. Visiting Landing / Sign-in Page ---');
  await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_landing_1440.png') });

  // Test responsive overflow on landing
  for (const w of [1440, 768, 390, 360]) {
    await page.setViewportSize({ width: w, height: 800 });
    await page.waitForTimeout(300);
    const overflow = await page.evaluate(() => {
      return {
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
      };
    });
    if (overflow.hasOverflow) {
      report.overflowIssues.push({ page: 'landing', width: w, ...overflow });
      console.log(`[OVERFLOW] Landing at ${w}px: scrollWidth=${overflow.scrollWidth}`);
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });

  // Check login form inputs
  const emailInput = await page.$('input[type="email"], input[name="email"], input#email');
  const passInput = await page.$('input[type="password"], input[name="password"], input#password');
  console.log('Inputs found:', !!emailInput, !!passInput);

  console.log('--- 2. Logging in as Buyer ---');
  if (emailInput && passInput) {
    await emailInput.fill(BUYER.email);
    await passInput.fill(BUYER.password);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_buyer_filled.png') });
    
    // Find submit button
    const submitBtn = await page.$('button[type="submit"], button:has-text("Sign In"), button:has-text("Log In")');
    if (submitBtn) {
      await Promise.all([
        page.waitForResponse(res => res.url().includes('/auth') || res.url().includes('/token') || res.status() >= 200, { timeout: 30000 }).catch(e => console.log('Wait response err:', e.message)),
        submitBtn.click()
      ]);
      await page.waitForTimeout(3000);
    }
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_after_buyer_login.png') });
  console.log('Current URL after buyer login:', page.url());

  // Check what is visible now
  const buyerPageContent = await page.evaluate(() => {
    return {
      title: document.title,
      headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent?.trim()),
      buttons: Array.from(document.querySelectorAll('button')).map(b => b.textContent?.trim()).filter(Boolean),
      links: Array.from(document.querySelectorAll('a')).map(a => ({ text: a.textContent?.trim(), href: a.getAttribute('href') })),
      bodySnippet: document.body.innerText.slice(0, 1000)
    };
  });
  report.buyerAudit.dashboard = buyerPageContent;
  console.log('Headings:', buyerPageContent.headings);
  console.log('Buttons:', buyerPageContent.buttons.slice(0, 10));

  // Check responsive overflow on authenticated dashboard
  for (const w of [1440, 768, 390, 360]) {
    await page.setViewportSize({ width: w, height: 800 });
    await page.waitForTimeout(300);
    const overflow = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
    }));
    if (overflow.hasOverflow) {
      report.overflowIssues.push({ page: 'buyer-dashboard', width: w, ...overflow });
      console.log(`[OVERFLOW] Buyer Dashboard at ${w}px: scrollWidth=${overflow.scrollWidth}`);
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });

  // Let's explore links and deals
  const dealLinks = await page.$$('a[href*="/deals/"], button:has-text("View Deal"), tr[data-deal-id], [data-testid="deal-card"]');
  console.log('Deal elements found:', dealLinks.length);

  // If there are deal links, click the first one
  const firstDeal = await page.$('a[href^="#/deals/"], a[href^="/deals/"]');
  if (firstDeal) {
    const href = await firstDeal.getAttribute('href');
    console.log('Clicking first deal link:', href);
    await firstDeal.click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_buyer_deal_detail.png') });

    // Inspect deal detail tabs / sections
    const tabs = await page.$$('button[role="tab"], nav button, [data-testid*="tab"]');
    console.log('Tabs found:', tabs.length);
    for (const t of tabs) {
      const text = await t.textContent();
      console.log('Tab:', text?.trim());
    }

    // Check deal detail responsive overflow
    for (const w of [1440, 768, 390, 360]) {
      await page.setViewportSize({ width: w, height: 800 });
      await page.waitForTimeout(300);
      const overflow = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
      }));
      if (overflow.hasOverflow) {
        report.overflowIssues.push({ page: 'buyer-deal-detail', width: w, ...overflow });
        console.log(`[OVERFLOW] Buyer Deal Detail at ${w}px: scrollWidth=${overflow.scrollWidth}`);
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });
  }

  // Save report
  fs.writeFileSync('/home/yashaswi/.gemini/antigravity/brain/dc9c2b1a-d602-472a-8039-5fff377eff3d/scratch/audit_report_phase1.json', JSON.stringify(report, null, 2));

  await browser.close();
  console.log('Phase 1 audit complete.');
}

audit().catch(err => {
  console.error('Audit failed:', err);
  process.exit(1);
});
