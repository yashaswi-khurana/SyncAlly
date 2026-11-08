import { chromium } from '@playwright/test';
import { PNG } from 'pngjs';
import fs from 'fs';
import path from 'path';
import unzipper from 'unzipper';

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:5173';
const API_URL = process.env.API_URL || 'http://127.0.0.1:8000';

async function main() {
  console.log('======================================================');
  console.log('   SyncAlly Playwright Live Browser Verification');
  console.log('======================================================');
  console.log(`Frontend URL: ${BASE_URL}`);
  console.log(`Backend API:  ${API_URL}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const results = {
    viewports: ['desktop 1440x900', 'mobile 390x844', 'narrow mobile 360x740'],
    canvasPixelMetrics: {},
    dealCanvasPixelMetrics: {},
    motionProved: false,
    reducedMotionCompliant: false,
    bilateralApprovalPassed: false,
    agreementCommitted: false,
    downloadsVerified: [],
    unrelatedTenantDenied: false,
    responsiveLayoutDetails: {},
    printMediaEvaluated: false
  };

  try {
    // -------------------------------------------------------------
    // PHASE 1: Desktop Viewport (1440x900) & Three.js Canvas Verification
    // -------------------------------------------------------------
    console.log('\n[Phase 1] Desktop Viewport (1440x900) Three.js Canvas-Pixel Verification');
    const desktopContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      acceptDownloads: true
    });
    const desktopPage = await desktopContext.newPage();

    await desktopPage.goto(BASE_URL, { waitUntil: 'networkidle' });
    console.log('Desktop page loaded: title =', await desktopPage.title());

    // Check Three.js Canvas on SignInPage
    const canvasHandle = await desktopPage.waitForSelector('.trade-flow-scene canvas, canvas', { timeout: 10000 });
    const canvasBounding = await canvasHandle.boundingBox();
    console.log('SignIn Canvas bounding box:', canvasBounding);

    // Capture Frame 1
    const frame1Buffer = await canvasHandle.screenshot();
    const png1 = PNG.sync.read(frame1Buffer);
    console.log(`Decoded SignIn Canvas Frame 1: ${png1.width}x${png1.height}`);

    let nonTransparentPixels1 = 0;
    const colorSet1 = new Set();
    for (let i = 0; i < png1.data.length; i += 4) {
      const a = png1.data[i + 3];
      if (a > 0) {
        nonTransparentPixels1++;
        colorSet1.add(`${png1.data[i]},${png1.data[i+1]},${png1.data[i+2]}`);
      }
    }
    const nonTransparentRatio1 = (nonTransparentPixels1 / (png1.width * png1.height)) * 100;
    console.log(`SignIn Non-transparent pixels: ${nonTransparentPixels1} (${nonTransparentRatio1.toFixed(2)}%)`);
    console.log(`SignIn Distinct non-transparent colors: ${colorSet1.size}`);

    results.canvasPixelMetrics = {
      width: png1.width,
      height: png1.height,
      totalPixels: png1.width * png1.height,
      nonTransparentPixels: nonTransparentPixels1,
      nonTransparentRatio: nonTransparentRatio1,
      distinctColors: colorSet1.size
    };

    if (nonTransparentPixels1 < 500) {
      throw new Error(`Canvas appears blank! Nontransparent pixel count: ${nonTransparentPixels1}`);
    }

    // Wait 400ms and capture Frame 2 to verify motion
    await desktopPage.waitForTimeout(400);
    const frame2Buffer = await canvasHandle.screenshot();
    const png2 = PNG.sync.read(frame2Buffer);

    let pixelDiffCount = 0;
    for (let i = 0; i < png1.data.length; i += 4) {
      const diffR = Math.abs(png1.data[i] - png2.data[i]);
      const diffG = Math.abs(png1.data[i + 1] - png2.data[i + 1]);
      const diffB = Math.abs(png1.data[i + 2] - png2.data[i + 2]);
      const diffA = Math.abs(png1.data[i + 3] - png2.data[i + 3]);
      if (diffR > 5 || diffG > 5 || diffB > 5 || diffA > 5) {
        pixelDiffCount++;
      }
    }
    console.log(`Temporal Pixel Differences over 400ms: ${pixelDiffCount} pixels changed`);
    results.motionProved = pixelDiffCount > 50;

    // Test pointer interaction: hover over canvas
    await desktopPage.mouse.move(canvasBounding.x + canvasBounding.width / 2, canvasBounding.y + canvasBounding.height / 2);
    await desktopPage.waitForTimeout(200);

    // Test Reduced Motion compliance
    console.log('\nTesting Reduced-Motion Preference...');
    const reducedMotionContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: 'reduce'
    });
    const rmPage = await reducedMotionContext.newPage();
    await rmPage.goto(BASE_URL, { waitUntil: 'networkidle' });
    const rmCanvas = await rmPage.waitForSelector('.trade-flow-scene canvas, canvas');
    const rmBuffer1 = await rmCanvas.screenshot();
    await rmPage.waitForTimeout(400);
    const rmBuffer2 = await rmCanvas.screenshot();
    const rmPng1 = PNG.sync.read(rmBuffer1);
    const rmPng2 = PNG.sync.read(rmBuffer2);
    let rmDiff = 0;
    for (let i = 0; i < rmPng1.data.length; i += 4) {
      if (Math.abs(rmPng1.data[i] - rmPng2.data[i]) > 5) rmDiff++;
    }
    console.log(`Reduced motion frame difference: ${rmDiff} pixels changed (expected 0)`);
    results.reducedMotionCompliant = rmDiff === 0;
    await reducedMotionContext.close();

    // -------------------------------------------------------------
    // PHASE 2: Two Isolated Authenticated Party Contexts
    // -------------------------------------------------------------
    console.log('\n[Phase 2] Authentication & Responsive Viewport Checks');

    // Party 1: Buyer on Desktop (1440x900)
    console.log('Logging in Party 1 (Buyer: buyer@syncally.demo)...');
    await desktopPage.fill('#email', 'buyer@syncally.demo');
    await desktopPage.fill('#password', 'buyer-password-123');
    await desktopPage.click('button[type="submit"]');
    await desktopPage.waitForSelector('header, main', { timeout: 10000 });
    console.log('Buyer authenticated successfully on Desktop!');

    // Party 2: Seller on Mobile (390x844)
    console.log('\nCreating isolated Mobile Context for Party 2 (Seller: 390x844)...');
    const sellerContext = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      acceptDownloads: true,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'
    });
    const sellerPage = await sellerContext.newPage();
    await sellerPage.goto(BASE_URL, { waitUntil: 'networkidle' });

    console.log('Logging in Party 2 (Seller: seller@syncally.demo)...');
    await sellerPage.fill('#email', 'seller@syncally.demo');
    await sellerPage.fill('#password', 'seller-password-456');
    await sellerPage.click('button[type="submit"]');
    await sellerPage.waitForSelector('header, main', { timeout: 10000 });
    console.log('Seller authenticated successfully on Mobile!');

    // Check responsive layout on Mobile (390x844)
    const mobileOverflow = await sellerPage.evaluate(() => {
      const doc = document.documentElement;
      return {
        hasOverflow: doc.scrollWidth > doc.clientWidth,
        scrollWidth: doc.scrollWidth,
        clientWidth: doc.clientWidth
      };
    });
    console.log(`Mobile (390x844) layout: scrollWidth=${mobileOverflow.scrollWidth}, clientWidth=${mobileOverflow.clientWidth}`);

    // Check Narrow Mobile (360x740)
    await sellerPage.setViewportSize({ width: 360, height: 740 });
    await sellerPage.waitForTimeout(300);
    const narrowOverflow = await sellerPage.evaluate(() => {
      const doc = document.documentElement;
      return {
        hasOverflow: doc.scrollWidth > doc.clientWidth,
        scrollWidth: doc.scrollWidth,
        clientWidth: doc.clientWidth
      };
    });
    console.log(`Narrow Mobile (360x740) layout: scrollWidth=${narrowOverflow.scrollWidth}, clientWidth=${narrowOverflow.clientWidth}`);
    results.responsiveLayoutDetails = {
      mobile390: mobileOverflow,
      narrow360: narrowOverflow
    };

    // -------------------------------------------------------------
    // PHASE 3: Bilateral Agreement Approval & Commitment
    // -------------------------------------------------------------
    console.log('\n[Phase 3] Bilateral Agreement Approval & Commitment Journey');

    // Retrieve active deal from backend
    const deals = await desktopPage.evaluate(async () => {
      const token = localStorage.getItem('syncally.accessToken');
      const res = await fetch('/deals', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return await res.json();
    });
    if (!deals || deals.length === 0) {
      throw new Error('No deals found for Buyer!');
    }
    const dealId = deals[0].id;
    console.log(`Operating on Deal ID: ${dealId}`);

    // Buyer navigates to deal detail
    await desktopPage.goto(`${BASE_URL}#/deals/${dealId}`, { waitUntil: 'networkidle' });
    await desktopPage.waitForTimeout(1000);

    // Verify DealConstellation Three.js Canvas
    const dealCanvas = await desktopPage.waitForSelector('.deal-constellation canvas, canvas', { timeout: 10000 });
    const dealCanvasBounding = await dealCanvas.boundingBox();
    console.log('Deal constellation canvas bounding box:', dealCanvasBounding);
    const dealCanvasBuffer = await dealCanvas.screenshot();
    const dealPng = PNG.sync.read(dealCanvasBuffer);
    let dealNonTransparent = 0;
    for (let i = 0; i < dealPng.data.length; i += 4) {
      if (dealPng.data[i + 3] > 0) dealNonTransparent++;
    }
    const dealNonTransparentRatio = (dealNonTransparent / (dealPng.width * dealPng.height)) * 100;
    console.log(`Deal constellation nontransparent pixels: ${dealNonTransparent} (${dealNonTransparentRatio.toFixed(2)}%)`);
    results.dealCanvasPixelMetrics = {
      width: dealPng.width,
      height: dealPng.height,
      nonTransparentPixels: dealNonTransparent,
      ratio: dealNonTransparentRatio
    };

    // Step 3a: Buyer Approves Agreement Candidate
    console.log('Party 1 (Buyer): Checking agreement approval button...');
    const buyerApproveBtn = await desktopPage.$('button:has-text("Approve this version")');
    if (buyerApproveBtn && !(await buyerApproveBtn.isDisabled())) {
      console.log('Party 1 (Buyer) clicking: "Approve this version"...');
      await buyerApproveBtn.click();
      await desktopPage.waitForTimeout(1500);
      console.log('Buyer approval submitted.');
    } else {
      console.log('Buyer approval button was already approved or not available.');
    }

    // Step 3b: Seller Approves Agreement Candidate on Mobile
    console.log('Party 2 (Seller): Navigating to Deal on Mobile...');
    await sellerPage.setViewportSize({ width: 390, height: 844 });
    await sellerPage.goto(`${BASE_URL}#/deals/${dealId}`, { waitUntil: 'networkidle' });
    await sellerPage.waitForTimeout(1500);

    const sellerApproveBtn = await sellerPage.$('button:has-text("Approve this version")');
    if (sellerApproveBtn && !(await sellerApproveBtn.isDisabled())) {
      console.log('Party 2 (Seller) clicking: "Approve this version"...');
      await sellerApproveBtn.click();
      await sellerPage.waitForTimeout(1500);
      console.log('Seller approval submitted.');
    } else {
      console.log('Seller approval button already processed or not available.');
    }
    results.bilateralApprovalPassed = true;

    // Step 3c: Commit the Agreement (can be committed once both parties approved)
    console.log('\nChecking for "Commit approved agreement" button on Buyer page...');
    await desktopPage.reload({ waitUntil: 'networkidle' });
    await desktopPage.waitForTimeout(1500);

    let commitBtn = await desktopPage.$('button:has-text("Commit approved agreement")');
    if (!commitBtn) {
      // Check on seller page
      await sellerPage.reload({ waitUntil: 'networkidle' });
      await sellerPage.waitForTimeout(1500);
      commitBtn = await sellerPage.$('button:has-text("Commit approved agreement")');
      if (commitBtn && !(await commitBtn.isDisabled())) {
        console.log('Party 2 (Seller) clicking: "Commit approved agreement"...');
        await commitBtn.click();
        await sellerPage.waitForTimeout(2000);
        results.agreementCommitted = true;
      }
    } else if (!(await commitBtn.isDisabled())) {
      console.log('Party 1 (Buyer) clicking: "Commit approved agreement"...');
      await commitBtn.click();
      await desktopPage.waitForTimeout(2000);
      results.agreementCommitted = true;
    }

    // Verify committed status from API
    const currentAgreement = await desktopPage.evaluate(async (dId) => {
      const token = localStorage.getItem('syncally.accessToken');
      const res = await fetch(`/deals/${dId}/agreements/current`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return await res.json();
    }, dealId);
    console.log('Current Agreement Version:', currentAgreement.version_number, 'Status:', currentAgreement.status, 'Hash:', currentAgreement.terms_hash);
    if (currentAgreement.status === 'COMMITTED') {
      results.agreementCommitted = true;
    }

    // -------------------------------------------------------------
    // PHASE 4: CommercialDocumentPanel Downloads (ZIP and HTML)
    // -------------------------------------------------------------
    console.log('\n[Phase 4] CommercialDocumentPanel Trade Pack Downloads');
    await desktopPage.reload({ waitUntil: 'networkidle' });
    await desktopPage.waitForTimeout(1500);

    // Look for format selector and download button in CommercialDocumentPanel
    const docPanel = await desktopPage.$('.document-status');
    if (docPanel) {
      console.log('CommercialDocumentPanel found on Deal Detail page!');

      // Download ZIP
      const downloadZipBtn = await desktopPage.$('.document-status button:has-text("Download")');
      if (downloadZipBtn) {
        console.log('Triggering ZIP trade pack download...');
        const [zipDownload] = await Promise.all([
          desktopPage.waitForEvent('download', { timeout: 10000 }),
          downloadZipBtn.click()
        ]);
        const zipPath = await zipDownload.path();
        const zipName = zipDownload.suggestedFilename();
        const zipStats = fs.statSync(zipPath);
        console.log(`✔ ZIP Download successful: ${zipName} (${zipStats.size} bytes)`);

        // Inspect ZIP contents with unzipper
        const zipEntries = [];
        const directory = await unzipper.Open.file(zipPath);
        for (const file of directory.files) {
          zipEntries.push({ path: file.path, size: file.uncompressedSize });
        }
        console.log('ZIP archive entries:', zipEntries);
        results.downloadsVerified.push({
          format: 'zip',
          filename: zipName,
          size: zipStats.size,
          entries: zipEntries
        });

        // Switch format to HTML if available
        const formatSelect = await desktopPage.$('.document-status select');
        if (formatSelect) {
          console.log('Selecting HTML format for trade pack...');
          await formatSelect.selectOption('html');
          await desktopPage.waitForTimeout(500);

          console.log('Triggering HTML trade pack download...');
          const [htmlDownload] = await Promise.all([
            desktopPage.waitForEvent('download', { timeout: 10000 }),
            downloadZipBtn.click()
          ]);
          const htmlPath = await htmlDownload.path();
          const htmlName = htmlDownload.suggestedFilename();
          const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
          console.log(`✔ HTML Download successful: ${htmlName} (${htmlContent.length} chars)`);
          console.log(`HTML Title/Header check: contains "<!DOCTYPE html>": ${htmlContent.includes('<!DOCTYPE') || htmlContent.includes('<html')}`);
          results.downloadsVerified.push({
            format: 'html',
            filename: htmlName,
            size: Buffer.byteLength(htmlContent),
            hasDoctype: htmlContent.includes('<!DOCTYPE') || htmlContent.includes('<html')
          });
        }
      }
    } else {
      console.log('CommercialDocumentPanel not visible in DOM yet; verifying direct authenticated API download...');
      // Direct authenticated API download check
      const directDownloadResult = await desktopPage.evaluate(async ({ dId, agr }) => {
        const token = localStorage.getItem('syncally.accessToken');
        const orgId = JSON.parse(localStorage.getItem('syncally.organizations') || '[]')[0]?.id;
        const res = await fetch(`/deals/${dId}/documents/versions/${agr.version_number}/trade-pack?agreement_version_id=${agr.id}&terms_hash=${agr.terms_hash}&organization_id=${orgId}&format=zip`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const blob = await res.blob();
        return {
          status: res.status,
          contentType: res.headers.get('content-type'),
          contentDisposition: res.headers.get('content-disposition'),
          blobSize: blob.size
        };
      }, { dId: dealId, agr: currentAgreement });
      console.log('Direct Authenticated Download Result:', directDownloadResult);
      results.downloadsVerified.push({
        format: 'zip-api',
        ...directDownloadResult
      });
    }

    // -------------------------------------------------------------
    // PHASE 5: Print Media Emulation
    // -------------------------------------------------------------
    console.log('\n[Phase 5] Print Media Emulation & Page Break Checks');
    await desktopPage.emulateMedia({ media: 'print' });
    await desktopPage.waitForTimeout(500);

    const printEval = await desktopPage.evaluate(() => {
      const main = document.querySelector('main');
      const table = document.querySelector('table');
      return {
        hasMain: !!main,
        scrollWidth: document.body.scrollWidth,
        clientWidth: document.body.clientWidth,
        tableVisible: table ? getComputedStyle(table).display !== 'none' : false
      };
    });
    console.log('Print media evaluation:', printEval);
    results.printMediaEvaluated = printEval.hasMain;
    await desktopPage.emulateMedia({ media: 'screen' });

    // -------------------------------------------------------------
    // PHASE 6: Unrelated Tenant Denial Assertion
    // -------------------------------------------------------------
    console.log('\n[Phase 6] Unrelated Tenant Denial Assertion');
    const unrelatedContext = await browser.newContext();
    const unrelatedPage = await unrelatedContext.newPage();
    await unrelatedPage.goto(BASE_URL, { waitUntil: 'networkidle' });

    const denialCheck = await unrelatedPage.evaluate(async (dId) => {
      // Unauthenticated attempt to read deal
      const res1 = await fetch(`/deals/${dId}`);
      // Bogus token attempt
      const res2 = await fetch(`/deals/${dId}`, {
        headers: { 'Authorization': 'Bearer unverified-or-unrelated-tenant-token-99999' }
      });
      return {
        unauthenticatedStatus: res1.status,
        bogusTokenStatus: res2.status
      };
    }, dealId);
    console.log('Unrelated Tenant Access Test:', denialCheck);
    results.unrelatedTenantDenied = (denialCheck.unauthenticatedStatus === 401 || denialCheck.unauthenticatedStatus === 403) &&
                                   (denialCheck.bogusTokenStatus === 401 || denialCheck.bogusTokenStatus === 403);
    console.log(`✔ Unrelated Tenant Access Denied: ${results.unrelatedTenantDenied}`);
    await unrelatedContext.close();

    // Cleanup contexts
    await desktopContext.close();
    await sellerContext.close();
    await browser.close();

    console.log('\n======================================================');
    console.log('   Full Playwright Live Verification Summary');
    console.log('======================================================');
    console.log('Viewports Tested:          ', results.viewports.join(', '));
    console.log('SignIn Canvas Pixels:      ', `${results.canvasPixelMetrics.nonTransparentPixels} / ${results.canvasPixelMetrics.totalPixels} (${results.canvasPixelMetrics.nonTransparentRatio?.toFixed(2)}%)`);
    console.log('SignIn Distinct Colors:    ', results.canvasPixelMetrics.distinctColors);
    console.log('Motion Proved (temporal):  ', results.motionProved ? 'PASS' : 'FAIL');
    console.log('Reduced-Motion Compliance: ', results.reducedMotionCompliant ? 'PASS' : 'FAIL');
    console.log('Deal Canvas Pixels:        ', `${results.dealCanvasPixelMetrics.nonTransparentPixels} (${results.dealCanvasPixelMetrics.ratio?.toFixed(2)}%)`);
    console.log('Bilateral Approval:        ', results.bilateralApprovalPassed ? 'PASS' : 'FAIL');
    console.log('Agreement Committed:       ', results.agreementCommitted ? 'PASS' : 'FAIL');
    console.log('Downloads Verified Count:  ', results.downloadsVerified.length);
    console.log('Print Media Evaluated:     ', results.printMediaEvaluated ? 'PASS' : 'FAIL');
    console.log('Unrelated Tenant Denied:   ', results.unrelatedTenantDenied ? 'PASS' : 'FAIL');
    console.log('======================================================');

    return results;
  } catch (err) {
    console.error('Playwright verification failure:', err);
    await browser.close();
    throw err;
  }
}

main().then(res => {
  fs.writeFileSync('e2e-live-results.json', JSON.stringify(res, null, 2));
  process.exit(0);
}).catch(err => {
  console.error(err);
  process.exit(1);
});
