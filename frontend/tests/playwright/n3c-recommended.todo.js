import {selectedConfigs, deploymentConfigs} from "./setup-test-environments";
// const { test, expect } = require('@playwright/test');
import {test, expect, } from '@playwright/test';

// Tests ---------------------------------------------------------------------------------------------------------------
let timeout = 20000;

// todo temp: toggle comment for development
// for (const envName of ['dev']) {
for (const envName in selectedConfigs) {
  
  const appUrl = deploymentConfigs[envName];
  
  test('N3C Recommended', async ({ page }) => {
    await page.goto(appUrl);
    await page.goto(appUrl + '/OMOPConceptSets');
    
    await page.getByTestId('Help / About').click();
    await page.getByRole('link', { name: 'N3C Recommended', exact: true }).click();
    // TODO: make some assertions
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
    await page.getByRole('link', { name: '12 removed , 12 added' }).click();
  });
}
