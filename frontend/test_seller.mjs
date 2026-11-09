import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const SCREENSHOT_DIR = '/home/yashaswi/.gemini/antigravity/brain/dc9c2b1a-d602-472a-8039-5fff377eff3d/scratch/screenshots';
const TARGET_URL = 'https://syncally-frontend.onrender.com/';

const SELLER = {
  email: 'shivanshgaur2p+seller@gmail.com',
  password: 'kyarakhopass'
};

async function testSellerView() {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  console.log('Logging in as SELLER...');
  await page.goto(TARGET_URL);
  await page.fill('input[type="email"]', SELLER.email);
  await page.fill('input[type="password"]', SELLER.password);
  await page.click('button:has-text("Enter workspace")');
  await page.waitForTimeout(2000);

  // Navigate explicitly to Workspace / Deals
  console.log('Navigating to Workspace...');
  await page.click('button:has-text("Workspace"), a:has-text("Workspace")');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'seller_workspace.png'), fullPage: true });

  const dealBtns = await page.$$('button:has-text("Open deal")');
  console.log('Seller deals found:', dealBtns.length);

  if (dealBtns.length > 0) {
    await dealBtns[0].click();
    console.log('Waiting 8 seconds on seller deal detail...');
    await page.waitForTimeout(8000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'seller_deal_detail.png'), fullPage: true });

    // Inspect seller specific buttons and permissions
    const sellerInfo = await page.evaluate(() => {
      return {
        headings: Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(h => h.textContent?.trim()),
        buttons: Array.from(document.querySelectorAll('button')).map(b => ({
          text: b.textContent?.trim(),
          disabled: b.disabled,
          className: b.className
        })),
        textSnippets: Array.from(document.querySelectorAll('.card, .panel, .deal-room')).map(c => c.innerText.slice(0, 200))
      };
    });
    fs.writeFileSync('/home/yashaswi/.gemini/antigravity/brain/dc9c2b1a-d602-472a-8039-5fff377eff3d/scratch/seller_detail_info.json', JSON.stringify(sellerInfo, null, 2));
  }

  await browser.close();
}

testSellerView().catch(err => {
  console.error(err);
  process.exit(1);
});
