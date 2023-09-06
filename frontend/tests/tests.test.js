/* eslint-disable */
/* # TermHub frontend tests

## Environments
Environments are specific setups / deployments where we want to run our tests, e.g. local / dev / prod. This information
is passed to the test script via a hyphen-delimited environmental variable, e.g. `ENVIRONMENTS=local-dev-prod npx
playwright test`, where  dev is short for 'development' and prod is short for 'production'.

## todo's: optimizations
    - Running on different deployments
    (a) diff file for each. maybe a commmon test file which is a function that takes appUrl, and all that local.test.js would do was set appUrl and then pass it to that func. Then could run via `npx playwright test FILENAME` and make a `make` command as shorthand
    (b) Loop: 1 file and loop over each deployment or pass a flag to select which one - (what's implemented here)
    (c) Command?: make a command that sets the URL in a file and then import that into the playwright test
    (d) playwright.config.js? - (didn't work; kinda makes sense since that url doesn't get passed)
*/
// @ts-check
const { test, expect } = require('@playwright/test');

// Config --------------------------------------------------------------------------------------------------------------
const deploymentConfigs = {
  local: 'http://127.0.0.1:3000',
  dev: 'https://icy-ground-0416a040f.2.azurestaticapps.net',
  prod: 'https://purple-plant-0f4023d0f.2.azurestaticapps.net',
};

// CLI --------------------------------------------------------------------------------------------------------------
// https://playwright.dev/docs/test-parameterize
let envsString = 'local-dev-prod';
if (process.env.ENVIRONMENTS) {
  envsString = process.env.ENVIRONMENTS;
}

const envs = envsString.split("-");
let selectedConfigs = {};
for (let key in deploymentConfigs) {
  if (envs.includes(key)) {
    selectedConfigs[key] = deploymentConfigs[key];
  }
}

// setUp ---------------------------------------------------------------------------------------------------------------
test.beforeAll(async () => {
  test.setTimeout(10000);  // 10 seconds
});

// Tests ---------------------------------------------------------------------------------------------------------------
for (const envName in selectedConfigs) {
  const appUrl = deploymentConfigs[envName];
  test(envName + ': ' + 'Main page - has title & heading', async ({ page }) => {
    await page.goto(appUrl);
    await expect(page).toHaveTitle(/TermHub/);  // Expect a title "to contain" a substring.
    await expect(page.getByRole('heading', { name: 'Within TermHub you can:' })).toBeVisible();
    // await expect(page.getByRole('heading', { name: 'Welcome to TermHub! Beta version 0.3.2' })).toBeVisible();
  });

  test(envName + ': ' + 'Help / about - hyperlink & title', async ({ page }) => {
    await page.goto(appUrl);
    await page.getByRole('link', { name: 'Help / About' }).click();
    await expect(page.getByRole('heading', { name: 'About TermHub\n' })).toBeVisible();
  });

  // todo: rename this as I add onto it. I think I want to do the workflow from search -> comparison
  test(envName + ': ' + 'Cset search - select, load, compare', async ({ page }) => {
    const testCodesetId = '1000002363';
    // Load page and click menu
    await page.goto(appUrl);

    // close alert panel if it appears
    if (envName === 'local') {
      const alertPanelClose = await page.waitForSelector('[data-testid=flexcontainer-Alerts] button');
      await alertPanelClose.click();
    }

    const searchWidget = await page.waitForSelector('#add-codeset-id');

    // Select item
    // todo: select a 2nd item
    // Attempt 2: keyboard (https://playwright.dev/docs/api/class-keyboard)
    await searchWidget.fill(testCodesetId);
    await searchWidget.press('ArrowDown');
    await searchWidget.press('Enter');

    // Load cset
    // todo: Change this back soon after next deployment after 2023/09/05; will have id soon.
    await page.locator('text="Load concept sets"').click();

    let codeset_ids = [testCodesetId];

    // could be simpler with only one codeset_id, but using same line below with more than one
    await expect(page).toHaveURL(`${appUrl}/OMOPConceptSets?${codeset_ids.map(d => 'codeset_ids='+d).join('&')}`);

    const firstRow = await page.waitForSelector('#related-csets-table #row-0');
    const cset = await firstRow.innerText();
    const firstRelatedCodesetId = (cset.match(/^\d+/) || [''])[0];
    expect(parseInt(firstRelatedCodesetId)).not.toBeNaN();
    codeset_ids.push(firstRelatedCodesetId);
    await firstRow.click();

    // Compare
    await page.getByRole('link', { name: 'Cset comparison' }).click();

    await expect(page).toHaveURL(`${appUrl}/cset-comparison?${codeset_ids.map(d => 'codeset_ids='+d).join('&')}`);
  });
}
