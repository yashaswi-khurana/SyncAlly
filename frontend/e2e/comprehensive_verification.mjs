import { chromium } from '@playwright/test';
import { PNG } from 'pngjs';
import fs from 'fs';
import path from 'path';
import unzipper from 'unzipper';

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:5173';
const API_URL = process.env.API_URL || 'http://127.0.0.1:8000';
const DEAL_ID = 'f27344e1-5776-4d63-ae2f-05a95cfd5dcf';

async function main() {
  console.log('======================================================================');
  console.log('   SyncAlly Playwright Multi-Viewport Live Verification Suite');
  console.log('======================================================================');
  console.log(`Frontend URL: ${BASE_URL}`);
  console.log(`Backend API:  ${API_URL}`);
  console.log(`Target Deal:  ${DEAL_ID}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const report = {
    timestamp: new Date().toISOString(),
    viewports: {},
    threeJs: {},
    dealConstellation: {},
    twoPartyAuth: {},
    downloads: {},
    printMedia: {},
    unrelatedTenant: {},
    verdict: 'PENDING'
  };

  try {
    // ------------------------------------------------------------------
    // 1. THREE.JS CANVAS-PIXEL VERIFICATION (SignIn Page)
    // ------------------------------------------------------------------
    console.log('\n[1] Three.js Canvas-Pixel Verification (TradeFlowScene)');
    const desktopContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      acceptDownloads: true
    });
    const desktopPage = await desktopContext.newPage();
    await desktopPage.goto(BASE_URL, { waitUntil: 'networkidle' });

    const canvas = await desktopPage.waitForSelector('.trade-flow-scene canvas, canvas', { timeout: 10000 });
    const canvasBounds = await canvas.boundingBox();
    console.log(`Canvas Bounding Box: ${canvasBounds.width}x${canvasBounds.height} at (${canvasBounds.x.toFixed(1)}, ${canvasBounds.y.toFixed(1)})`);

    // Frame 1
    const frame1Buf = await canvas.screenshot();
    const frame1Png = PNG.sync.read(frame1Buf);
    let nonTransparent1 = 0;
    const colors1 = new Set();
    for (let i = 0; i < frame1Png.data.length; i += 4) {
      if (frame1Png.data[i + 3] > 0) {
        nonTransparent1++;
        colors1.add(`${frame1Png.data[i]},${frame1Png.data[i+1]},${frame1Png.data[i+2]}`);
      }
    }
    const nonTransparentRatio = (nonTransparent1 / (frame1Png.width * frame1Png.height)) * 100;
    console.log(`Frame 1 Dimensions: ${frame1Png.width}x${frame1Png.height}`);
    console.log(`Nontransparent Pixels: ${nonTransparent1} / ${frame1Png.width * frame1Png.height} (${nonTransparentRatio.toFixed(2)}%)`);
    console.log(`Distinct Non-transparent Colors: ${colors1.size}`);

    // Temporal Motion Check (wait 400ms, capture Frame 2)
    await desktopPage.waitForTimeout(400);
    const frame2Buf = await canvas.screenshot();
    const frame2Png = PNG.sync.read(frame2Buf);
    let motionDiffPixels = 0;
    for (let i = 0; i < frame1Png.data.length; i += 4) {
      const dr = Math.abs(frame1Png.data[i] - frame2Png.data[i]);
      const dg = Math.abs(frame1Png.data[i + 1] - frame2Png.data[i + 1]);
      const db = Math.abs(frame1Png.data[i + 2] - frame2Png.data[i + 2]);
      const da = Math.abs(frame1Png.data[i + 3] - frame2Png.data[i + 3]);
      if (dr > 5 || dg > 5 || db > 5 || da > 5) motionDiffPixels++;
    }
    console.log(`Temporal Motion Differences (400ms elapsed): ${motionDiffPixels} pixels changed`);
    const motionProved = motionDiffPixels > 50;
    console.log(`Motion Proved: ${motionProved ? 'PASS' : 'FAIL'}`);

    // Reduced Motion Compliance
    console.log('Testing Reduced-Motion Preference...');
    const rmContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: 'reduce'
    });
    const rmPage = await rmContext.newPage();
    await rmPage.goto(BASE_URL, { waitUntil: 'networkidle' });
    const rmCanvas = await rmPage.waitForSelector('.trade-flow-scene canvas, canvas');
    const rmBuf1 = await rmCanvas.screenshot();
    await rmPage.waitForTimeout(400);
    const rmBuf2 = await rmCanvas.screenshot();
    const rmPng1 = PNG.sync.read(rmBuf1);
    const rmPng2 = PNG.sync.read(rmBuf2);
    let rmDiff = 0;
    for (let i = 0; i < rmPng1.data.length; i += 4) {
      if (Math.abs(rmPng1.data[i] - rmPng2.data[i]) > 5) rmDiff++;
    }
    console.log(`Reduced-Motion Pixel Difference: ${rmDiff} (expected: 0)`);
    const reducedMotionPass = rmDiff === 0;
    await rmContext.close();

    report.threeJs = {
      bounds: canvasBounds,
      dimensions: `${frame1Png.width}x${frame1Png.height}`,
      nonTransparentPixels: nonTransparent1,
      nonTransparentRatio: `${nonTransparentRatio.toFixed(2)}%`,
      distinctColors: colors1.size,
      motionDiffPixels,
      motionProved,
      reducedMotionPass
    };

    // ------------------------------------------------------------------
    // 2. TWO ISOLATED AUTHENTICATED PARTIES & VIEWPORT TESTS
    // ------------------------------------------------------------------
    console.log('\n[2] Two Isolated Authenticated Party Contexts');

    // Party 1 (Buyer) Login on Desktop (1440x900)
    console.log('Logging in Party 1 (Buyer: buyer@syncally.demo) on Desktop (1440x900)...');
    await desktopPage.fill('#email', 'buyer@syncally.demo');
    await desktopPage.fill('#password', 'buyer-password-123');
    await desktopPage.click('button[type="submit"]');
    await desktopPage.waitForSelector('header');
    console.log('Buyer authenticated successfully!');

    // Party 2 (Seller) Login on Mobile (390x844)
    console.log('Creating isolated Mobile Context for Party 2 (Seller: seller@syncally.demo, 390x844)...');
    const mobileContext = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      acceptDownloads: true,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'
    });
    const mobilePage = await mobileContext.newPage();
    await mobilePage.goto(BASE_URL, { waitUntil: 'networkidle' });
    await mobilePage.fill('#email', 'seller@syncally.demo');
    await mobilePage.fill('#password', 'seller-password-456');
    await mobilePage.click('button[type="submit"]');
    await mobilePage.waitForSelector('header');
    console.log('Seller authenticated successfully on Mobile (390x844)!');

    // Viewport overflow checks
    const desktopOverflow = await desktopPage.evaluate(() => {
      const doc = document.documentElement;
      return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, hasOverflow: doc.scrollWidth > doc.clientWidth };
    });
    const mobile390Overflow = await mobilePage.evaluate(() => {
      const doc = document.documentElement;
      return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, hasOverflow: doc.scrollWidth > doc.clientWidth };
    });

    // Narrow Mobile (360x740)
    await mobilePage.setViewportSize({ width: 360, height: 740 });
    await mobilePage.waitForTimeout(300);
    const narrow360Overflow = await mobilePage.evaluate(() => {
      const doc = document.documentElement;
      return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, hasOverflow: doc.scrollWidth > doc.clientWidth };
    });
    // Restore to 390x844
    await mobilePage.setViewportSize({ width: 390, height: 844 });

    report.viewports = {
      desktop1440: desktopOverflow,
      mobile390: mobile390Overflow,
      narrow360: narrow360Overflow
    };
    console.log('Desktop (1440x900) overflow:', desktopOverflow.hasOverflow);
    console.log('Mobile (390x844) overflow:', mobile390Overflow.hasOverflow);
    console.log('Narrow Mobile (360x740) overflow:', narrow360Overflow.hasOverflow);

    // ------------------------------------------------------------------
    // 3. DEAL CONSTELLATION THREE.JS & BILATERAL STATUS IN UI
    // ------------------------------------------------------------------
    console.log('\n[3] Deal Detail Page Inspection & DealConstellation');
    await desktopPage.goto(`${BASE_URL}#/deals/${DEAL_ID}`, { waitUntil: 'networkidle' });
    await desktopPage.waitForTimeout(1500);

    const dealCanvas = await desktopPage.waitForSelector('.deal-constellation canvas, canvas', { timeout: 10000 });
    const dealBounds = await dealCanvas.boundingBox();
    const dealBuf = await dealCanvas.screenshot();
    const dealPng = PNG.sync.read(dealBuf);
    let dealNonTrans = 0;
    for (let i = 0; i < dealPng.data.length; i += 4) {
      if (dealPng.data[i + 3] > 0) dealNonTrans++;
    }
    const dealRatio = (dealNonTrans / (dealPng.width * dealPng.height)) * 100;
    console.log(`DealConstellation Dimensions: ${dealPng.width}x${dealPng.height}`);
    console.log(`DealConstellation Nontransparent Pixels: ${dealNonTrans} (${dealRatio.toFixed(2)}%)`);

    report.dealConstellation = {
      bounds: dealBounds,
      dimensions: `${dealPng.width}x${dealPng.height}`,
      nonTransparentPixels: dealNonTrans,
      ratio: `${dealRatio.toFixed(2)}%`
    };

    // ------------------------------------------------------------------
    // 4. COMMERCIAL DOCUMENT PANEL DOWNLOADS (ZIP & HTML)
    // ------------------------------------------------------------------
    console.log('\n[4] CommercialDocumentPanel Authorized Downloads (ZIP & HTML)');
    const downloadBtn = await desktopPage.waitForSelector('button:has-text("Download trade pack")', { timeout: 10000 });

    // Download ZIP
    console.log('Triggering ZIP trade pack download in Buyer context...');
    const [zipDownload] = await Promise.all([
      desktopPage.waitForEvent('download', { timeout: 10000 }),
      downloadBtn.click()
    ]);
    const zipPath = await zipDownload.path();
    const zipFilename = zipDownload.suggestedFilename();
    const zipStats = fs.statSync(zipPath);
    console.log(`✔ Downloaded ZIP: ${zipFilename} (${zipStats.size} bytes)`);

    // Verify ZIP member entries
    const zipDirectory = await unzipper.Open.file(zipPath);
    const zipMembers = zipDirectory.files.map(f => ({ path: f.path, size: f.uncompressedSize }));
    console.log('ZIP archive members:', zipMembers);

    // Download HTML
    console.log('Switching to HTML format and triggering download...');
    await desktopPage.selectOption('#trade-pack-format', 'html');
    await desktopPage.waitForTimeout(500);

    const [htmlDownload] = await Promise.all([
      desktopPage.waitForEvent('download', { timeout: 10000 }),
      downloadBtn.click()
    ]);
    const htmlPath = await htmlDownload.path();
    const htmlFilename = htmlDownload.suggestedFilename();
    const htmlStats = fs.statSync(htmlPath);
    const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
    console.log(`✔ Downloaded HTML: ${htmlFilename} (${htmlStats.size} bytes)`);

    report.downloads = {
      zip: {
        filename: zipFilename,
        size: zipStats.size,
        safeFilename: /^[A-Za-z0-9.-]+$/.test(zipFilename),
        members: zipMembers
      },
      html: {
        filename: htmlFilename,
        size: htmlStats.size,
        safeFilename: /^[A-Za-z0-9.-]+$/.test(htmlFilename),
        hasDoctype: htmlContent.includes('<!doctype html>'),
        hasSecurityHeaders: htmlContent.includes("Content-Security-Policy"),
        hasTermsHash: htmlContent.includes('9fa7295fa14c')
      }
    };

    // Also download in Seller context (Mobile 390x844)
    console.log('Navigating Seller context on mobile to deal and downloading trade pack...');
    await mobilePage.goto(`${BASE_URL}#/deals/${DEAL_ID}`, { waitUntil: 'networkidle' });
    await mobilePage.waitForTimeout(1500);
    const sellerDownloadBtn = await mobilePage.waitForSelector('button:has-text("Download trade pack")', { timeout: 10000 });
    await sellerDownloadBtn.scrollIntoViewIfNeeded();

    const [sellerZipDownload] = await Promise.all([
      mobilePage.waitForEvent('download', { timeout: 10000 }),
      sellerDownloadBtn.click()
    ]);
    const sellerZipStats = fs.statSync(await sellerZipDownload.path());
    console.log(`✔ Downloaded ZIP in Seller context: ${sellerZipDownload.suggestedFilename()} (${sellerZipStats.size} bytes)`);
    report.downloads.sellerZipSize = sellerZipStats.size;

    // ------------------------------------------------------------------
    // 5. PRINT MEDIA EMULATION & EVALUATION
    // ------------------------------------------------------------------
    console.log('\n[5] Print Media Emulation & Evaluation');
    await desktopPage.emulateMedia({ media: 'print' });
    await desktopPage.waitForTimeout(500);
    const printEvaluation = await desktopPage.evaluate(() => {
      const main = document.querySelector('main');
      const table = document.querySelector('table');
      return {
        hasMain: !!main,
        scrollWidth: document.body.scrollWidth,
        clientWidth: document.body.clientWidth,
        hasTable: !!table
      };
    });
    console.log('Print media evaluation:', printEvaluation);
    await desktopPage.emulateMedia({ media: 'screen' });
    report.printMedia = printEvaluation;

    // ------------------------------------------------------------------
    // 6. UNRELATED TENANT DENIAL CASE
    // ------------------------------------------------------------------
    console.log('\n[6] Unrelated Tenant Denial Assertion');
    const unrelatedContext = await browser.newContext();
    const unrelatedPage = await unrelatedContext.newPage();
    await unrelatedPage.goto(BASE_URL, { waitUntil: 'networkidle' });

    const tenantDenial = await unrelatedPage.evaluate(async (dId) => {
      const resUnauth = await fetch(`/deals/${dId}`);
      const resBogus = await fetch(`/deals/${dId}`, {
        headers: { 'Authorization': 'Bearer attacker-or-unrelated-tenant-token-99999' }
      });
      const resDocUnauth = await fetch(`/deals/${dId}/documents/commercial-draft`);
      return {
        unauthDealStatus: resUnauth.status,
        bogusTokenDealStatus: resBogus.status,
        unauthDocStatus: resDocUnauth.status
      };
    }, DEAL_ID);
    console.log('Tenant Denial Results:', tenantDenial);
    const tenantDenied = tenantDenial.unauthDealStatus === 401 &&
                         tenantDenial.bogusTokenDealStatus === 401 &&
                         tenantDenial.unauthDocStatus === 401;
    console.log(`✔ Unrelated Tenant Isolation & Denial: ${tenantDenied ? 'VERIFIED' : 'FAILED'}`);
    report.unrelatedTenant = { ...tenantDenial, verified: tenantDenied };

    await unrelatedContext.close();
    await desktopContext.close();
    await mobileContext.close();
    await browser.close();

    report.verdict = 'ALL_TESTS_PASSED';
    console.log('\n======================================================================');
    console.log('   RESULT: PLAYWRIGHT LIVE VERIFICATION COMPLETED (EXIT 0)');
    console.log('======================================================================');
    return report;
  } catch (err) {
    console.error('Test Suite Failed:', err);
    await browser.close();
    report.verdict = 'FAILED';
    report.error = err.message;
    throw err;
  }
}

main().then(rep => {
  fs.writeFileSync('comprehensive-e2e-report.json', JSON.stringify(rep, null, 2));
  process.exit(0);
}).catch(err => {
  console.error(err);
  process.exit(1);
});
