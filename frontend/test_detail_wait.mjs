import { chromium } from '@playwright/test';
import path from 'path';

const SCREENSHOT_DIR = '/home/yashaswi/.gemini/antigravity/brain/dc9c2b1a-d602-472a-8039-5fff377eff3d/scratch/screenshots';
const TARGET_URL = 'https://syncally-frontend.onrender.com/';

const BUYER = {
  email: 'shivanshgaur2p+buyer@gmail.com',
  password: 'kyarakhopass'
};

async function testDealDetail() {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  page.on('console', msg => console.log('BROWSER LOG:', msg.type(), msg.text()));
  page.on('response', res => {
    console.log('HTTP', res.status(), res.url().split('?')[0]);
  });

  await page.goto(TARGET_URL);
  await page.fill('input[type="email"]', BUYER.email);
  await page.fill('input[type="password"]', BUYER.password);
  await page.click('button:has-text("Enter workspace")');
  await page.waitForTimeout(2000);

  // Click open deal
  console.log('Clicking Open deal...');
  await page.click('button:has-text("Open deal")');

  console.log('Waiting 8 seconds on deal detail...');
  await page.waitForTimeout(8000);

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'buyer_deal_detail_waited.png'), fullPage: true });

  const states = await page.evaluate(() => {
    return {
      bodyText: document.body.innerText,
      hasLoading: document.body.innerText.includes('Loading'),
      loadingTexts: Array.from(document.querySelectorAll('*'))
        .filter(el => el.children.length === 0 && el.textContent.includes('Loading'))
        .map(el => el.textContent.trim())
    };
  });

  console.log('Still loading elements:', states.loadingTexts);
  await browser.close();
}

testDealDetail().catch(err => {
  console.error(err);
  process.exit(1);
});
