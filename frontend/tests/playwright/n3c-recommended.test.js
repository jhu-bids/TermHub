import {selectedConfigs, deploymentConfigs} from "./setup-test-environments";
// const { test, expect } = require('@playwright/test');
import {test, expect, } from '@playwright/test';

/*
use this test in for loop

test('test', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  await page.goto('http://localhost:3000/OMOPConceptSets');
  await page.getByTestId('Help / About').click();
  await page.getByRole('link', { name: 'N3C Recommended comparison' }).click();
  await page.getByRole('link', { name: '12 removed , 12 added' }).click();
  await page.locator('html').click({
    button: 'right'
  });
});
 */
// Tests ---------------------------------------------------------------------------------------------------------------
let timeout = 20000;

for (const envName in selectedConfigs) {
  const config = selectedConfigs[envName];
  test.describe(`Graph algorithm tests for ${config.test_name}`, () => {
    const appUrl = deploymentConfigs[envName];

    test('N3C Recommended', async ({ page }) => {
      // await page.goto(appUrl);
      await page.goto(appUrl + '/OMOPConceptSets');

      await page.getByTestId('Help / About').click();
      await page.getByRole('link', { name: 'N3C Recommended', exact: true }).click();
      // TODO: make some assertions
      await expect(page.getByText(
          'Downloading N3C Recommended concept sets to bundle-report-N3C_Recommended.csv in your downloads folder.'
      )).toBeVisible();
    });

    test('N3C Recommended comparison', async ({ page }) => {
      await page.goto(appUrl);
      await page.goto(appUrl + '/OMOPConceptSets');

      await page.getByTestId('Help / About').click();
      await page.getByRole('link', { name: 'N3C Recommended comparison' }).click();
      // todo: maybe try to dynamically select whatever row it is that has changes, rather than static case
      await page.getByRole('row', { name: 'Expand Row CARDIOMYOPATHIES' }).getByTestId('expander-button-undefined').click();
      // TODO: how to select the table dynamically? I want to assert that it shows rows are removed an added
      //  - but the selector id is really weird: <div class="sc-jXbUNg cyUjzM rdt_ExpanderRow">. has another <div>, then
      //    another <p>, then a <table id="n3ccompdiff">
      //    Ahhh! We need unique IDs. It should be something like "n3ccompdiff-removed-CARDIOMYOPATHIES" (or whatever the
      //    cset ID for that is).
      // TODO: After solving the above, assert rows added/removed

      // TODO: Next, find some way to dynamically select the hyperink in the rightmost column
      // TODO: What do I expect to happen next? it says "downloading..."
      // await page.getByRole('link', { name: '12 removed , 12 added' }).click();
      //    commented that out. there isn't a link with that text anymore
    });

  });
}
