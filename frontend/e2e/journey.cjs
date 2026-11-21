const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');

(async () => {
  const url = process.env.EDA_URL || 'http://127.0.0.1:8001';
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const explorer = url + '/data-explorer';
    await page.goto(explorer);
    const run = await (await page.request.get(url + '/api/v1/runs/current')).json();
    const gold = await (await page.request.get(url + '/api/v1/runs/' + run.run_id + '/tables')).json();
    const goldList = page.getByRole('list', { name: 'Gold tables' });
    const option = (list, name) => list.getByRole('button', { name, exact: true });
    await expect(option(goldList, 'cost_monthly')).toHaveAttribute('aria-pressed', 'true');
    assert.deepEqual((await goldList.getByRole('button').allTextContents()).map(label => label.trim()), gold.tables.map(table => table.name));

    const lineage = page.getByRole('region', { name: 'Table lineage' });
    const panel = page.getByRole('region', { name: 'Selected table' });
    await expect(lineage.getByRole('link', { name: /^cost_facts / })).toBeVisible();
    await expect(lineage.getByRole('region', { name: 'Bronze lineage' })).toHaveCount(0);
    await option(goldList, 'licence_monthly').click();
    await expect(lineage.getByRole('link', { name: /^contracts / })).toBeVisible();
    await expect(lineage.getByRole('link', { name: /^subject / })).toHaveCount(0);

    await page.locator('summary').filter({ hasText: 'Silver tables' }).click();
    const silverList = page.getByRole('list', { name: 'Silver tables' });
    await option(silverList, 'contracts').click();
    await expect(page).toHaveURL(/table=silver%3Acontracts/);
    for (const name of ['ai_subscriptions.csv', 'saas_contracts.csv']) {
      await expect(lineage.getByRole('link', { name: new RegExp('^' + name + ' ') })).toBeVisible();
    }
    await expect(lineage.getByRole('region', { name: 'Gold lineage' })).toHaveCount(0);
    await page.reload();
    await expect(panel.getByRole('heading', { name: 'contracts' })).toBeVisible();
    await panel.getByRole('link', { name: 'Inspect table' }).click();
    await expect(page.getByRole('combobox', { name: 'Cleaned table' })).toHaveValue('contracts');

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(explorer + '?table=gold%3Alicence_monthly');
    await expect(lineage.getByRole('link', { name: /^contracts / })).toBeVisible();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await option(goldList, 'analysis_run').click();
    await expect(lineage.getByText('No documented inputs in this layer.')).toBeVisible();

    await page.route('**/api/v1/data-quality?scope=full', route => route.fulfill({ status: 503, json: {} }));
    await page.goto(explorer + '?table=silver%3Acontracts');
    await expect(page.getByText('Bronze catalog unavailable.')).toBeVisible();
    await expect(panel.getByRole('heading', { name: 'contracts' })).toBeVisible();
    await expect(lineage.getByRole('link', { name: /^ai_subscriptions.csv / })).toHaveCount(0);
    console.log('Gold table list, upstream lineage, deep links, inspector, mobile layout and partial availability passed.');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
