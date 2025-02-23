/* eslint-disable */
/* # TermHub basic frontend tests

## todo's: optimizations
    - Running on different deployments
    (a) diff file for each. maybe a commmon test file which is a function that takes appUrl, and all that local.test.js would do was set appUrl and then pass it to that func. Then could run via `npx playwright test FILENAME` and make a `make` command as shorthand
    (b) Loop: 1 file and loop over each deployment or pass a flag to select which one - (what's implemented here)
    (c) Command?: make a command that sets the URL in a file and then import that into the playwright test
    (d) playwright.config.js? - (didn't work; kinda makes sense since that url doesn't get passed)
*/

import { time } from "node:console";
import {selectedConfigs, deploymentConfigs} from "./setup-test-environments";
import {parse} from 'csv-parse/sync';

const { test, expect } = require('@playwright/test');
const { PerformanceObserver, performance } = require('node:perf_hooks');

const experiment = 'no_cache';

// const configsToRun = 'local'; // only run these tests in local for now
const configsToRun = selectedConfigs; // uncomment to run on dev or prod

/* setUp ---------------------------------------------------------------------------------------------------------------
test.beforeAll(async () => {
  test.setTimeout(10000);  // 10 seconds
}); */

/*
| test_type           | test_name              | expected result | codeset_ids                                                      |
|---------------------|------------------------|-----------------|------------------------------------------------------------------|
| many small          | neurological           | fast            | 1000002657, 241882304, 488007883, 1000087163                     |
| single 2000         | autoimmune 1           | not bad         | 101398605,                                                       |
| mixed 6000 to 21000 | Sulfonylureas          |                 | 417730759, 423850600, 966671711, 577774492                       |
| mixed 30 to 3000    | autoimmune 2           |                 | 101398605, 947369784, 287650725, 283328624, 115052941            |
| single 30000        | antibiotics 1          |                 | 909552172                                                        |
| many 5000           | many-5000-what-is-this |                 | 295817643, 613313946, 613313946, 781483910, 986994148, 671755133 |
| single small        | single-small-again     |                 | 1000002363                                                       |
 */
const tests_csv = `
testType,testName,codeset_ids,timeoutSeconds
single small,single-small,1000002363,30
many small,many-small,"1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299",45
single small,single-small-second-time,1000002363,30
`;
const hold_tests = `
mixed 6000 to 21000,Sulfonylureas,"417730759, 423850600, 966671711, 577774492",120
single 2000,autoimmune 1,101398605,180
mixed 30 to 3000,autoimmune 2,"101398605, 947369784, 287650725, 283328624, 115052941",240
single 30000,antibiotics 1,909552172,180
`;

const tests = parse(tests_csv, {columns: true, skip_empty_lines: true});
const run_how = 'playwright';
const code_being_tested = 'develop:ba7fc6e no performance optimizations';

async function getMem(page, prefix, fields) {
  const mem = await page.evaluate(([prefix, fields]) => {
    // @ts-ignore
    // @ts-ignore
    const {jsHeapSizeLimit, totalJSHeapSize, usedJSHeapSize} = window.performance.memory;
    let stuff = {};
    if (fields.includes('limit')) stuff[prefix+'Limit'] = jsHeapSizeLimit;
    if (fields.includes('used')) stuff[prefix+'Used'] = usedJSHeapSize;
      // [prefix+'Total']: totalJSHeapSize,
      //[prefix+'cacheLength']: (localStorage.dataCache || '').length,
    /*
    // @ts-ignore
    const wc = window.dataCacheW.getWholeCache();
    for (const prop in wc) {
      stuff[prefix+prop] = Object.keys(wc[prop]).length;
    }
    */
    return stuff;
  }, [prefix, fields]);
  return mem;
}

console.log(`running ${tests.length} tests for ${JSON.stringify(configsToRun)}`);
for (const envName in configsToRun) {
  const appUrl = deploymentConfigs[envName];
  /*
    in basic-functions, needed to change this to
        const appUrl = deploymentConfigs[envName] + '/OMOPConceptSets';
    but that won't work here. maybe needed to change it because something
    changed in the way the app redirects from / to /OMOPConceptSets. so
    i'm not sure the tests in this file will work without dealing with
    that somehow.
   */
  for (const csets_test of tests) {
    let {testType, testName, codeset_ids, timeoutSeconds} = csets_test;
    codeset_ids = codeset_ids.split(',');
    const testTitle = `${testName}_on_${envName}`;
    test(testTitle, async({page, browser, context}, testInfo) => {
      testInfo.attach('started', {body: `${testName} on ${envName}`})
      console.log(`running ${testName} on ${envName}`);
      page.setDefaultTimeout(timeoutSeconds * 2000);  // need extra time here i think. single-small timed out with 30 seconds
                                                      // or maybe that was a temporary problem with indented-concept-list performance
      /* if (testName === 'single-small-second-time') {
      } */

      /**
       * @param {string} prefix
       */

      let firstCols = { stepCompleted: 'start', experiment: 'no_cache', };
      let lastCols = { testType, run_how, envName, }
      let durations = {};
      let mem = {};
      let report = {...firstCols, ...lastCols};
      testInfo.attach('report', {body: JSON.stringify(report), contentType: 'application/json'});

      performance.mark('start');
      await page.goto(appUrl);
      firstCols.stepCompleted = 'homepage';

      // await page.evaluate(() => (window.performance.mark('start-async')))
      performance.mark('homepage');
      let memStart = {};
      memStart = await getMem(page, 'homepage', ['limit','used']);
      // const [startLimit, startTotal, startUsed] = memStuff;
      mem = { ...memStart };
      testInfo.attach('report', {body: JSON.stringify(report), contentType: 'application/json'});

      let pageUrl = `${appUrl}/OMOPConceptSets?optimization_experiment=no_cache&${codeset_ids.map(d => `codeset_ids=${d}`).join("&")}`
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
      durations.searchLoaded = searchLoaded.duration / 1000;
      memStart = await getMem(page, 'searchLoaded', ['used']);
      mem = {...mem, ...memStart };
      firstCols.stepCompleted = 'searchLoaded';
      report = {...firstCols, ...durations, ...mem, ...lastCols};
      testInfo.attach('report', {body: JSON.stringify(report), contentType: 'application/json'});

      // page.setDefaultTimeout(120000); // already did this, but maybe it needs doing again? or not?
      const compPageLink = await page.waitForSelector('[data-testid="Analyze and author"]');
      await compPageLink.click();
      console.log('going to comparison page');
      await expect(page.locator('[data-testid=comp-page-loading]')).toBeAttached({timeout: timeoutSeconds * 1000});
      console.log('loading comparison page');
      await expect(page.locator('[data-testid=comp-page-loaded]')).toBeAttached({timeout: timeoutSeconds * 1000});
      console.log('loaded comparison page');
      performance.mark('comparison page loaded');
      const comparisonLoaded = performance.measure("comparisonLoaded", "search page loaded", "comparison page loaded");
      durations.comparisonLoaded = comparisonLoaded.duration / 1000;
      memStart = await getMem(page, 'comparisonLoaded', ['used']);
      mem = {...mem, ...memStart };
      firstCols.stepCompleted = 'comparisonLoaded';
      report = {...firstCols, ...durations, ...mem, ...lastCols};

      // testInfo.attach('search loaded', {body: rptKeys + '\n' + rptVals, contentType: 'text/plain'});
      testInfo.attach('report', {body: JSON.stringify(report), contentType: 'application/json'})

      //Performance measure
      // await page.evaluate(() => (window.performance.measure("overall", "Perf:Started", "Perf:Ended")))
      // getting Error: page.evaluate: DOMException: Failed to execute 'measure' on 'Performance': The mark 'Perf:Started' does not exist.

    });
  }
}

/*

// Tests ---------------------------------------------------------------------------------------------------------------
for (const envName in configsToRun) {
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
