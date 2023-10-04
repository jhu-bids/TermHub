/* eslint-disable */
/* # TermHub basic frontend tests

## todo's: optimizations
    - Running on different deployments
    (a) diff file for each. maybe a commmon test file which is a function that takes appUrl, and all that local.test.js would do was set appUrl and then pass it to that func. Then could run via `npx playwright test FILENAME` and make a `make` command as shorthand
    (b) Loop: 1 file and loop over each deployment or pass a flag to select which one - (what's implemented here)
    (c) Command?: make a command that sets the URL in a file and then import that into the playwright test
    (d) playwright.config.js? - (didn't work; kinda makes sense since that url doesn't get passed)
*/
// @ts-check

import {selectedConfigs, deploymentConfigs} from "./setup-test-environments";

const { test, expect } = require('@playwright/test');
const { PerformanceObserver, performance } = require('node:perf_hooks');

/* setUp ---------------------------------------------------------------------------------------------------------------
test.beforeAll(async () => {
  test.setTimeout(10000);  // 10 seconds
}); */

const tests = [
  ['name', 'codeset_ids'],
  ['Sulfonylureas', [ 417730759, 423850600, 966671711, 577774492 ]],
  ['Antibiotics', [ 909552172 ]],
]

// Tests ---------------------------------------------------------------------------------------------------------------
for (const envName in selectedConfigs) {
  const appUrl = deploymentConfigs[envName];
  console.log('testing ' + appUrl);
  test(envName + ': ' + 'Main page - has title & heading', async ({ page }) => {
    await page.goto(appUrl);
    await expect(page).toHaveTitle(/TermHub/);  // Expect a title "to contain" a substring.
    await expect(page.getByRole('heading', { name: 'Within TermHub you can:' })).toBeVisible();
    // await expect(page.getByRole('heading', { name: 'Welcome to TermHub! Beta version 0.3.2' })).toBeVisible();
  });

  test(envName + ': ' + 'Sulfonylureas concept sets causing cache error', async ({ page, browser }) => {

    // page.setDefaultTimeout(10000);

    let codeset_ids = [ 417730759, 423850600, 966671711, 577774492 ];

    let pageUrl = `${appUrl}/OMOPConceptSets?${codeset_ids.map(d => `codeset_ids=${d}`).join("&")}`

    /*
    const session = await page.context().newCDPSession(page)
    await session.send("Performance.enable")

    await page.goto(pageUrl);

    console.log("=============CDP Performance Metrics===============")
    let performanceMetrics = await session.send("Performance.getMetrics")
    console.log(performanceMetrics.metrics)
    */

    console.log("========== Start Tracing Perf ===========")
    await page.evaluate(() => (window.performance.mark('Perf:Started')))
    // await browser.startTracing(page, { path: './perfTraces.json', screenshots: true })

    await page.goto(pageUrl);

    //Using Performanc.mark API
    await page.evaluate(() => (window.performance.mark('Perf:Navigated')))

    // close alert panel if it appears
    if (envName === 'local') {
      const alertPanelClose = await page.waitForSelector('[data-testid=flexcontainer-Alerts] button');
      await page.evaluate(() => (window.performance.mark('Perf:Closed-alert-panel')))
      await alertPanelClose.click();
    }

    await page.evaluate(() => (window.performance.mark('Perf:PageLoading')))

    const searchWidget = await page.waitForSelector('#add-codeset-id');

    // await browser.stopTracing()
    // return;

    await expect(page.getByRole('heading', { name: '[DM]Sulfonylureas (v7)' })).toBeVisible();


    await page.evaluate(() => (window.performance.mark('Perf:Ended')))

    //Performance measure
    // await page.evaluate(() => (window.performance.measure("overall", "Perf:Started", "Perf:Ended")))
    // getting Error: page.evaluate: DOMException: Failed to execute 'measure' on 'Performance': The mark 'Perf:Started' does not exist.

    //To get all performance marks
    const getAllMarksJson = await page.evaluate(() => (JSON.stringify(window.performance.getEntriesByType("mark"))))
    const getAllMarks = await JSON.parse(getAllMarksJson)
    console.log('window.performance.getEntriesByType("mark")', getAllMarks)

    const getAllMeasuresJson = await page.evaluate(() => (JSON.stringify(window.performance.getEntriesByType("measure"))))
    const getAllMeasures = await JSON.parse(getAllMeasuresJson)
    console.log('window.performance.getEntriesByType("measure")', getAllMeasures)
    // await page.press('[title="Search"]', 'Enter')
    // await browser.stopTracing()
    console.log("======= Stop Tracing ============")
  });

  /*
  test(envName + ': ' + 'Antibiotics', async ({ page }) => {
    let codeset_ids = [ 909552172 ];

    let pageUrl = `${appUrl}/OMOPConceptSets?${codeset_ids.map(d => `codeset_ids=${d}`).join("&")}`

    await page.goto(pageUrl);

    // close alert panel if it appears
    if (envName === 'local') {
      const alertPanelClose = await page.waitForSelector('[data-testid=flexcontainer-Alerts] button');
      await alertPanelClose.click();
    }

    const searchWidget = await page.waitForSelector('#add-codeset-id');

    await expect(page.getByRole('heading', { name: '[DM]Sulfonylureas (v7)' })).toBeVisible();
  });
  */
}
