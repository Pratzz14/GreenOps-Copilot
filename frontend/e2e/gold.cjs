/* Published Gold tab, scenario and export regressions against the case dataset. */
const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');

(async () => {
  const url = process.env.EDA_URL || 'http://127.0.0.1:8001';
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      const requests = [];
      page.on('request', request => requests.push(new URL(request.url()).pathname));
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => {
        if (message.type() === 'error' || message.type() === 'warning') errors.push(message.text());
      });
      await page.goto(url + '/data-explorer');
      await expect(page).toHaveURL(url + '/data-explorer');
      await expect(page).toHaveTitle(/GreenOps/);
      await page.getByRole('tab', { name: 'Gold' }).click();
      const gold = page.getByRole('tabpanel', { name: 'Gold' });
      await expect(gold.getByRole('heading', { name: 'Business insights and decisions.' })).toBeVisible();
      const baseline = gold.getByRole('region', { name: 'Gold baseline' });
      await expect(baseline.getByText(/^CHF\s+463['’]471\.49$/)).toBeVisible();
      await expect(baseline.getByText(/^128['’]061\.32 kWh$/)).toBeVisible();
      await expect(baseline.getByText(/^13['’]218\.68 kg CO₂$/)).toBeVisible();
      await expect(baseline.getByText(/^35['’]667 recorded charges$/)).toBeVisible();
      await expect(gold.getByText(/114 missing amounts/)).toBeVisible();

      const catalog = gold.getByRole('list', { name: 'Published Gold tables' });
      const tableRow = name => catalog.locator('.layer-catalog-row').filter({
        has: page.getByText(name, { exact: true }),
      });
      await expect(gold.getByText(/14 tables in this run/)).toBeVisible();
      await expect(catalog.locator('.layer-catalog-row')).toHaveCount(14);
      await expect(gold.getByRole('heading', { name: 'Savings package' })).not.toBeVisible();
      assert.equal(requests.some(path => /\/tables\/|\/api\/v1\/packages\//.test(path)), false);

      const costs = tableRow('cost_monthly');
      await costs.locator('summary').first().click();
      await expect(costs.getByText('One row per', { exact: true })).toBeVisible();
      await expect(costs.getByText('Silver cost facts, billing geography, and ownership', { exact: true })).toBeVisible();
      await expect(costs.getByRole('table', { name: 'cost_monthly' })).toBeVisible();
      await expect(costs.getByRole('columnheader', { name: 'recorded_cost_chf' })).toBeVisible();
      await costs.getByRole('button', { name: 'Next', exact: true }).click();
      await expect(costs.getByText(/26–50 of/)).toBeVisible();
      await costs.locator('summary').first().click();
      await expect(costs.getByRole('table', { name: 'cost_monthly' })).not.toBeVisible();

      const run = tableRow('analysis_run');
      await run.locator('summary').first().click();
      await expect(run.getByRole('cell', { name: /^16['’]500\.00$/ })).toBeVisible();
      await run.locator('summary').first().click();

      const factor = tableRow('factor');
      await factor.locator('summary').first().click();
      await expect(factor.getByText('0.330000000000', { exact: true })).toBeVisible();
      await factor.getByText('Column schema', { exact: true }).click();
      await expect(factor.getByText('DECIMAL(28,12)', { exact: true }).first()).toBeVisible();
      await factor.locator('summary').first().click();

      const protection = tableRow('protection_window');
      await protection.locator('summary').first().click();
      await expect(protection.getByRole('columnheader', { name: 'starts_at' })).toBeVisible();
      await expect(protection.getByText(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/).first()).toBeVisible();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await protection.locator('summary').first().click();

      if (process.env.GOLD_QA_SCREENSHOTS) {
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: path.join(os.tmpdir(), `greenops-gold-tables-${viewport.width}.png`) });
      }
      const overview = gold.getByText('Detailed overview', { exact: true });
      await overview.click();
      await expect(gold.getByText('Targets unassessed', { exact: true })).toBeVisible();
      await gold.getByLabel('Group by').selectOption('tool');
      await expect(gold.getByRole('columnheader', { name: 'Tool', exact: true })).toBeVisible();
      await expect(gold.getByRole('rowheader', { name: 'Data platform development' })).toBeVisible();
      await gold.getByLabel('Period').selectOption('2026-08-01');
      await expect(gold.getByRole('rowheader', { name: 'Data platform development' })).toBeVisible();
      await gold.getByLabel('Assumption scenario').selectOption('low');
      await expect(baseline.getByText(/^46['’]725\.28 kWh$/)).toBeVisible();
      await gold.getByLabel('Savings horizon').selectOption('first_year');
      await expect(gold.getByText('21 Nov 2026 to 20 Nov 2027')).toBeVisible();
      await gold.getByText('Conditional package illustration', { exact: true }).click();
      await expect(gold.getByText('Human review required', { exact: true })).toBeVisible();

      const production = gold.locator('article').filter({
        has: page.getByRole('heading', { name: 'Block blanket production shutdown' }),
      });
      await expect(production.getByText('Blocked', { exact: true })).toBeVisible();
      await production.getByText('View evidence').click();
      await expect(production.getByText(/T-1029.*Finance closing work/)).toBeVisible();
      await expect(gold.getByText(/103 weekend days/).first()).toBeVisible();
      await expect(gold.getByText(/747\.97.*359 observed days/)).toBeVisible();

      for (const [name, header] of [
        ['Draft baseline CSV', 'parameter,must_or_bonus,value_low,value_mid,value_high,unit,source,calculation_or_assumption'],
        ['Draft measures CSV', 'measure_id,description,resource_or_source,change,effort_person_days'],
      ]) {
        const href = await gold.getByRole('link', { name, exact: true }).getAttribute('href');
        const response = await page.request.get(url + href);
        assert.equal(response.status(), 200);
        assert.ok((await response.text()).startsWith(header));
        assert.match(response.headers()['content-disposition'], /draft-template_/);
      }

      await gold.getByText('Factors and calculation assumptions', { exact: true }).click();
      await expect(gold.getByText('Switzerland electricity consumption, direct CO2', { exact: true })).toBeVisible();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await overview.click();
      await expect(gold.getByRole('heading', { name: 'Savings package' })).not.toBeVisible();
      await expect(catalog).toBeVisible();
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('Desktop and mobile Gold checks passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
