import {selectedConfigs, deploymentConfigs} from "./setup-test-environments";
import {isEqual} from 'lodash';
import {createSearchParams, useSearchParams, /* useLocation, Navigate, */ } from "react-router-dom";
// const { test, expect } = require('@playwright/test');
import {test, expect, } from '@playwright/test';

import { GraphContainer, makeGraph, } from '../../src/state/GraphState';
// import {graphOptionsInitialState, GraphOptionsProvider, useGraphOptions, } from '../../src/state/AppState';

import singleSmallTestData from '../test-data/singleSmallGraph.json';
import manySmallGraphContainerGraphData
  from '../test-data/manySmallGraphContainerGraphData.json';
import asthmaGraphData from '../test-data/asthmaExampleGraphData.json';
// diagramCase: last copied from test_graph.py test_get_missing_in_between_nodes(): 2024/02/11
// edges only. see https://github.com/jhu-bids/TermHub/blob/develop/docs/graph.md
import _diagramCase from '../test-data/diagramCase.json';
import {convertToArrayOfStrings} from '../testUtils';
let diagramCase = convertToArrayOfStrings(_diagramCase);


let testCases = [singleSmallTestData, manySmallGraphContainerGraphData, asthmaGraphData, diagramCase];
testCases = [singleSmallTestData, ];

// Tests ---------------------------------------------------------------------------------------------------------------

let timeout = 20000;

for (const envName in selectedConfigs) {
  const appUrl =
      deploymentConfigs[envName] +
      '/cset-comparison?' +
      codeset_ids.map(d => `codeset_ids=${d}`).join('&');
  for (const testData of testCases) {
    const {test_name, codeset_ids, graphData, roots, leaves, firstRow, } = testData;

    test.describe(`On ${envName} with case ${test_name}`, () => {
      test.describe(`GraphOptions and GraphContainer Tests`, async () => {
        let page;

        /*
        test.beforeAll(async ({browser}) => {
          page = await browser.newPage();
          await page.goto(appUrl);
        });
        test(envName + ': ' + 'Help / about - hyperlink & title', async ({ page }) => {
          await page.goto(appUrl);
          await page.getByRole('link', { name: 'Help / About' }).click();
          await expect(page.getByRole('heading', { name: /About (VS-Hub|TermHub)/ })).toBeVisible();
        });
         */

        test('GraphContainer tests', async ({page}) => {
          await page.goto(appUrl);

          // await page.waitForSelector('table:has-text("Concept name")');
          // Check the Concept ID in the first row
          // await page.pause();  // claude.ai recommended for debugging, but I don't understand what it does
          const conceptIdCell = await page.locator('#row-0 div:nth-child(11)', {timeout});
          await expect(conceptIdCell).toHaveText(firstRow.concept_id+'', {timeout});

          const gc = new GraphContainer(graphData);

          await page.evaluate(() => window.dispatchGraphOptions({
            gc,
            type: 'TOGGLE_NODE_EXPANDED',
            nodeId: firstRow.concept_id,
            direction: 'expand',
          }));

          const result = await page.evaluate((/*{graphData, roots, firstRow}*/) => {
            // const [graphOptions, graphOptionsDispatch] = useGraphOptions();
            const gc = new GraphContainer(graphData);
            let displayedRows = gc.getDisplayedRows(window.graphOptions);

            const initialRoots = gc.roots;
            const initialDisplayedRows = displayedRows.map(r => r.concept_id);
            const initialFirstRow = displayedRows[0];

            const expandedChildRows = displayedRows.slice(1,
                initialFirstRow.childIds.length + 1).map(r => r.concept_id);

            return {
              initialRoots,
              initialDisplayedRows,
              initialFirstRow,
              expandedChildRows,
            };
          }, singleSmallTestData);

          console.log("RESULT", result);
          expect(result.initialRoots).toStrictEqual(singleSmallTestData.roots);
          expect(result.initialDisplayedRows).toEqual(singleSmallTestData.roots);
          expect(result.initialFirstRow).toEqual(singleSmallTestData.firstRow);
          expect(result.expandedChildRows).toEqual(singleSmallTestData.firstRow.childIds);
        });
        test('codeset_ids in search params', async () => {
          expect(async ({ page }) => {
            const url = new URL(page.url());
            console.log(codeset_ids);
            return isEqual(url.searchParams.getAll('codeset_ids').sort(), codeset_ids.sort());
          }).toBeTruthy();

          // console.log(page);
          const result = await page.evaluate((arg1, arg2, arg3) => {
            console.log("console.log HERE", {arg1, arg2, arg3});
            return {arg1, arg2, arg3};
            // const [graphOptions] = useGraphOptions();
            // console.log(graphOptions);
            // return graphOptions;
          });
          console.log("RESULT:", result);
          /*
          expect(result).toEqual(graphOptionsInitialState);
           */
        });

        await expect(async ({ page }) => {
          const url = new URL(page.url());
          return url.pathname === 'cset-comparison';
        }).toBeTruthy();
      });
    });

    /*
    test(envName + ': ' + 'Main page - has title & heading', async ({ page }) => {
      await page.goto(appUrl);
      await expect(page).toHaveTitle(/(VS-Hub|TermHub)/);  // Expect a title "to contain" a substring.
      await expect(page.getByRole('heading', { name: /Within (VS-Hub|TermHub) you can:/ })).toBeVisible();
    });

    test(envName + ': ' + 'Help / about - hyperlink & title', async ({ page }) => {
      await page.goto(appUrl);
      await page.getByRole('link', { name: 'Help / About' }).click();
      await expect(page.getByRole('heading', { name: /About (VS-Hub|TermHub)/ })).toBeVisible();
    });

    // todo: rename this as I add onto it. I think I want to do the workflow from search -> comparison
    test(envName + ': ' + 'Cset search - select, load, compare', async ({ page }) => {
      const testCodesetId = '1000002363';
      // Load page and click menu
      await page.goto(appUrl);

      // close alert panel if it appears  // I think it's turned off
      /*
      if (envName === 'local') {
        const alertPanelClose = await page.waitForSelector('[data-testid=flexcontainer-Alerts] button');
        await alertPanelClose.click();
      }
      * /

      const searchWidget = await page.waitForSelector('#add-codeset-id');

      // Select item
      // todo: select a 2nd item
      // Attempt 2: keyboard (https://playwright.dev/docs/api/class-keyboard)
      await searchWidget.fill(testCodesetId);
      await searchWidget.press('ArrowDown');
      await searchWidget.press('Enter');

      // Load cset
      // todo: Change this back soon after next deployment after 2023/09/05; will have id soon.
      // await page.locator('text="Load concept sets"').click();

      let codeset_ids = [testCodesetId];

      await expect(async ({ page }) => {
        const url = new URL(page.url());
        return isEqual(url.searchParams.getAll('codeset_ids').sort(), codeset_ids.sort());
      }).toBeTruthy();


      const firstRow = await page.waitForSelector('#related-csets-table #row-0');
      const cset = await firstRow.innerText();
      const firstRelatedCodesetId = (cset.match(/^\d+/) || [''])[0];
      expect(parseInt(firstRelatedCodesetId)).not.toBeNaN();
      codeset_ids.push(firstRelatedCodesetId);
      await firstRow.click();

      // Compare
      await page.getByRole('link', { name: 'Cset comparison' }).click();
      // await expect(page).toHaveURL(`${appUrl}/cset-comparison?${codeset_ids.map(d => 'codeset_ids='+d).join('&')}`);
      // that broke because there's other stuff in query string

      await expect(async ({ page }) => {
        const url = new URL(page.url());
        return url.pathname === 'cset-comparison';
      }).toBeTruthy();

      await expect(async ({ page }) => {
        const url = new URL(page.url());
        return isEqual(url.searchParams.getAll('codeset_ids').sort(), codeset_ids.sort());
      }).toBeTruthy();
    });
     */
  }
}
