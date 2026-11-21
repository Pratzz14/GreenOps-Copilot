const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');

(async () => {
  const url = process.env.EDA_URL || 'http://127.0.0.1:8001';
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [{ width: 1440, height: 1080 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => {
        if (['error', 'warning'].includes(message.type())) errors.push(message.text());
      });
      await page.goto(url + '/data-explorer');
      await page.getByRole('tab', { name: 'Silver' }).click();
      const silver = page.getByRole('tabpanel', { name: 'Silver' });
      await expect(silver.getByRole('heading', { name: 'Silver overview' })).toBeVisible();
      await expect(silver.getByText('Ready with unresolved issues')).toBeVisible({ timeout: 20000 });
      await expect(silver.getByRole('region', { name: 'Silver build summary' }).getByText(/^CHF\s+463['’]471\.49$/)).toBeVisible();
      await expect(silver.getByText('Financial coverage is incomplete.', { exact: false })).toBeVisible();
      await expect(silver.locator('details[open]')).toHaveCount(0);
      await expect(silver.getByLabel('Silver table catalog')).toHaveCount(0);
      await expect(silver.getByLabel('Silver data and cost analysis')).toHaveCount(0);
      await page.screenshot({ path: path.join(os.tmpdir(), `greenops-silver-${viewport.width}.png`) });

      const catalogToggle = silver.locator('.layer-disclosure > summary').filter({ hasText: 'Browse Silver tables' });
      await catalogToggle.click();
      await expect(silver.getByRole('region', { name: 'Cleaned source tables' }).locator('.layer-catalog-row')).toHaveCount(13);
      await expect(silver.getByRole('region', { name: 'New tables' }).locator('.layer-catalog-row')).toHaveCount(6);
      const azure = silver.getByRole('region', { name: 'Cleaned source tables' })
        .locator('.layer-catalog-row').filter({ hasText: 'azure_costs.csv' });
      await expect(azure.getByText('Parsed billing dates and JSON tags', { exact: false })).toBeHidden();
      await azure.locator(':scope > details > summary').click();
      await expect(azure.getByText('Parsed billing dates and JSON tags', { exact: false })).toBeVisible();
      await expect(azure.getByText(/^\d+ missing amount$/)).toBeVisible();
      await azure.getByText('Transformation audit entries').click();
      await expect(azure.getByText('parse date', { exact: false })).toBeVisible();
      await expect(azure.getByRole('heading', { name: 'Cleaning steps' })).toBeVisible();
      const expectedInputs = {
        cost_facts: ['azure_costs', 'aws_costs', 'hoster_invoice', 'ai_usage', 'ai_subscriptions', 'saas_contracts', 'exchange_rates'],
        usage_facts: ['data_platform_usage', 'server_metrics_weekly', 'ai_usage'],
        assets: ['server_inventory'],
        contracts: ['ai_subscriptions', 'saas_contracts'],
        ownership: ['mapping_departments_tools'],
        resource_relationships: ['azure_costs', 'aws_costs', 'hoster_invoice', 'server_inventory', 'mapping_departments_tools'],
      };
      const newTables = silver.getByRole('region', { name: 'New tables' });
      for (const [name, inputs] of Object.entries(expectedInputs)) {
        const title = page.locator('summary > strong').and(page.getByText(`${name}.csv`, { exact: true }));
        const newTable = newTables.locator('.layer-catalog-row').filter({ has: title });
        const toggle = newTable.locator(':scope > details > summary');
        await toggle.click();
        await expect(newTable.getByRole('heading', { name: 'Why this table was created' })).toBeVisible();
        await expect(newTable.getByRole('heading', { name: 'How this table was created' })).toBeVisible();
        const sources = newTable.getByRole('list', { name: 'Cleaned Silver inputs' }).getByRole('listitem');
        await expect(sources).toHaveText(inputs.map(input => `${input}.csv`));
        await toggle.click();
      }
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
      await catalogToggle.click();
      await expect(azure).toBeHidden();
      await silver.locator('.layer-disclosure > summary').filter({ hasText: 'Explore data and costs' }).click();

      const open = async title => {
        const section = silver.locator('details.analysis-section').filter({
          has: page.locator('summary').filter({ hasText: new RegExp('^' + title + '$') }),
        });
        await section.locator(':scope > summary').click();
        return section;
      };
      const rows = await open('Cleaned table browser');
      await expect(rows.getByRole('button', { name: 'Inspect row 2', exact: true })).toBeVisible();
      await rows.getByRole('button', { name: 'Next', exact: true }).click();
      await expect(rows.locator('.pagination')).toContainText('21–40');
      await rows.getByLabel('Record status').selectOption('duplicate');
      await rows.getByRole('button', { name: /Inspect row/ }).first().click();
      await expect(silver.getByRole('button', { name: 'Inspect retained original' })).toBeVisible();
      await silver.getByRole('button', { name: 'Inspect retained original' }).click();
      await expect(silver.getByText(/ · Bronze logical row .* · accepted/)).toBeVisible();
      await open('Profiling');
      await expect(silver.getByText('expected type', { exact: true })).toBeVisible();
      const distribution = await open('Distributions');
      await expect(distribution.locator('.chart-canvas svg')).toBeVisible();
      await expect(distribution.getByLabel('Silver measurement').locator('option').filter({ hasText: 'Converted CHF' })).toHaveCount(1);
      await open('Before versus after');
      await expect(silver.getByText('matched bronze missing', { exact: true })).toBeVisible();
      await silver.getByRole('button', { name: 'Baseline period' }).click();
      await expect(silver.getByRole('button', { name: 'Baseline period' })).toHaveAttribute('aria-pressed', 'true');
      const issues = await open('Unresolved issues');
      await issues.getByLabel('Issue code').selectOption('missing_amount');
      await expect(issues.getByText('Source amount is unknown.').first()).toBeVisible();
      await open('Financial reconciliation');
      await expect(silver.getByText('agrees with total', { exact: true })).toBeVisible();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
      await page.getByRole('tab', { name: 'Gold' }).click();
      await expect(page.getByRole('tabpanel', { name: 'Gold' }).getByRole('heading', {
        name: 'Business insights and decisions.',
      })).toBeVisible();
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('Silver desktop and mobile exploration passed.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
