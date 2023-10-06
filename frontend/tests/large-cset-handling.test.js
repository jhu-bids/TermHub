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
import {parse} from 'csv-parse/sync';

const { test, expect } = require('@playwright/test');
const { PerformanceObserver, performance } = require('node:perf_hooks');

/* setUp ---------------------------------------------------------------------------------------------------------------
test.beforeAll(async () => {
  test.setTimeout(10000);  // 10 seconds
}); */

const tests_csv = `
testType,testName,codeset_ids
single small,single-small,1000002363
many small,many-small,"1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299"
mixed 6000 to 21000,Sulfonylureas,"417730759, 423850600, 966671711, 577774492"
single 2000,autoimmune 1,101398605
mixed 30 to 3000,autoimmune 2,"101398605, 947369784, 287650725, 283328624, 115052941"
single 30000,antibiotics 1,909552172
single small,single-small-second-time,1000002363
`;
const hold_tests = `
`;

const tests = parse(tests_csv, {columns: true, skip_empty_lines: true});
const run_how = 'playwright';
const code_being_tested = 'develop:ba7fc6e no performance optimizations';

async function getMem(page, prefix) {
  const mem = await page.evaluate(([prefix]) => {
    // @ts-ignore
    // @ts-ignore
    const {jsHeapSizeLimit, totalJSHeapSize, usedJSHeapSize} = window.performance.memory;
    const stuff = {
      [prefix+'Limit']: jsHeapSizeLimit,
      [prefix+'Total']: totalJSHeapSize,
      [prefix+'Used']: usedJSHeapSize,
      [prefix+'cacheLength']: (localStorage.dataCache || '').length,
    };
    // @ts-ignore
    const wc = window.dataCacheW.getWholeCache();
    for (const prop in wc) {
      stuff[prefix+prop] = Object.keys(wc[prop]).length;
    }
    return stuff;
  }, [prefix]);
  return mem;
}

for (const csets_test of tests) {
  let {testType, testName, codeset_ids} = csets_test;
  codeset_ids = codeset_ids.split(',');
  for (const envName in selectedConfigs) {
    const appUrl = deploymentConfigs[envName];
    test(testName, async({page}, testInfo) => {
      console.log(`running ${testName} on ${envName}`);
      page.setDefaultTimeout(120000);

      /**
       * @param {string} prefix
       */

      let report = {
        testName, testType, codeset_ids, run_how, envName,
        page: 'search',
      }

      performance.mark('start');
      await page.goto(appUrl);
      // await page.evaluate(() => (window.performance.mark('start-async')))
      let memStart = {};
      memStart = await getMem(page, 'start');
      // const [startLimit, startTotal, startUsed] = memStuff;
      report = {...report, ...memStart };

      let pageUrl = `${appUrl}/OMOPConceptSets?${codeset_ids.map(d => `codeset_ids=${d}`).join("&")}`
      await page.goto(pageUrl);

      // close alert panel if it appears
      if (envName === 'local') {
        const alertPanelClose = await page.waitForSelector('[data-testid=flexcontainer-Alerts] button');
        await alertPanelClose.click();
      }

      const searchWidget = await page.waitForSelector('#add-codeset-id');

      await expect(page.locator(`[data-testid=codeset_id-${codeset_ids[0]}]`)).toBeAttached();
      performance.mark('search page loaded');
      const searchLoaded = performance.measure("searchLoaded", "start", "search page loaded");
      report.searchLoaded = searchLoaded.duration;
      memStart = await getMem(page, 'searchLoaded');
      delete memStart.searchLoadedLimit;
      delete memStart.searchLoadedTotal;
      report = {...report, ...memStart };

      page.setDefaultTimeout(120000);

      const compPageLink = await page.waitForSelector('[data-testid="Cset comparison"]');
      await compPageLink.click();
      console.log('going to comparison page');
      await expect(page.locator('[data-testid=comp-page-loading]')).toBeAttached({timeout: 60000});
      console.log('loading comparison page');
      await expect(page.locator('[data-testid=comp-page-loaded]')).toBeAttached({timeout: 60000});
      console.log('loaded comparison page');
      performance.mark('comparison page loaded');
      const comparisonLoaded = performance.measure("comparisonLoaded", "search page loaded", "comparison page loaded");
      report.comparisonLoaded = comparisonLoaded.duration;
      memStart = await getMem(page, 'comparisonLoaded');
      delete memStart.comparisonLoadedLimit;
      delete memStart.comparisonLoadedTotal;
      report = {...report, ...memStart };

      // testInfo.attach('search loaded', {body: rptKeys + '\n' + rptVals, contentType: 'text/plain'});
      testInfo.attach('search-loaded', {body: JSON.stringify(report), contentType: 'application/json'})

      //Performance measure
      // await page.evaluate(() => (window.performance.measure("overall", "Perf:Started", "Perf:Ended")))
      // getting Error: page.evaluate: DOMException: Failed to execute 'measure' on 'Performance': The mark 'Perf:Started' does not exist.

    });
  }
}

/*

// Tests ---------------------------------------------------------------------------------------------------------------
for (const envName in selectedConfigs) {
  const appUrl = deploymentConfigs[envName];
  console.log('testing ' + appUrl);
  /*
  test(envName + ': ' + 'Main page - has title & heading', async ({ page }) => {
    await page.goto(appUrl);
    await expect(page).toHaveTitle(/TermHub/);  // Expect a title "to contain" a substring.
    await expect(page.getByRole('heading', { name: 'Within TermHub you can:' })).toBeVisible();
    // await expect(page.getByRole('heading', { name: 'Welcome to TermHub! Beta version 0.3.2' })).toBeVisible();
  });
  * /

  test(envName + ': ' + 'Sulfonylureas concept sets causing cache error', async ({ page, browser, context }) => {

    await page.evaluate(() => (window.performance.mark('Perf:Started')))

    // console.log({browser, context, page});
    // page.setDefaultTimeout(10000);

    let report = {

    }

    let codeset_ids = [ 417730759, 423850600, 966671711, 577774492 ];

    let pageUrl = `${appUrl}/OMOPConceptSets?${codeset_ids.map(d => `codeset_ids=${d}`).join("&")}`

    /*
    const session = await page.context().newCDPSession(page)
    await session.send("Performance.enable")

    await page.goto(pageUrl);

    console.log("=============CDP Performance Metrics===============")
    let performanceMetrics = await session.send("Performance.getMetrics")
    console.log(performanceMetrics.metrics)
    * /

    await page.evaluate(() => (window.performance.mark('Perf:Started')))
    // await browser.startTracing(page, { path: './perfTraces.json', screenshots: true })

    await page.goto(pageUrl);

    // close alert panel if it appears
    if (envName === 'local') {
      const alertPanelClose = await page.waitForSelector('[data-testid=flexcontainer-Alerts] button');
      await alertPanelClose.click();
    }

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
  * /
}
*/
