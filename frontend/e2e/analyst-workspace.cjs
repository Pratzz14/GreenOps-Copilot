/* Real Silver data, combined API and SPA, desktop and narrow screens. */
const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');

(async () => {
  const url = process.env.EDA_URL || 'http://127.0.0.1:8001';
  const browser = await chromium.launch({ headless: true });
  const screenshots = process.env.ANALYSIS_QA_SCREENSHOTS;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (['warning', 'error'].includes(message.type()) && !message.text().includes('422')) errors.push(message.text());
    });
    await page.goto(url + '/data-explorer');
    await expect(page).toHaveURL(url + '/data-explorer');
    await expect(page.getByRole('heading', { name: 'Data journey', exact: true })).toBeVisible();
    await page.getByRole('tab', { name: 'Silver' }).click();
    await expect(page.getByRole('heading', { name: 'Silver overview' })).toBeVisible();
    await page.getByRole('link', { name: 'Analyst Workspace' }).click();
    await expect(page).toHaveURL(url + '/analysis');
    await page.goBack();
    await expect(page).toHaveURL(url + '/data-explorer');
    await page.goForward();
    await expect(page).toHaveURL(url + '/analysis');
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Analyst Workspace' })).toBeVisible();
    await expect(page).toHaveTitle(/GreenOps/);

    const run = () => page.getByRole('button', { name: 'Run analysis' }).click();
    const result = page.getByRole('region', { name: 'Analysis results' });
    const waitForRun = async () => {
      const response = page.waitForResponse(response => response.url().endsWith('/analysis/query'));
      await run();
      const completed = await response;
      expect(completed.status()).toBe(200);
      const { metadata } = await completed.json();
      await expect(result.getByRole('link', { name: 'Export CSV' }))
        .toHaveAttribute('href', `/api/v1/analysis/results/${metadata.id}/csv`);
    };
    const editor = page.getByLabel('Read-only SQL');
    await expect(editor).toBeVisible();
    await editor.fill('SELECT COUNT(*) AS observations FROM cost_facts');
    const manual = page.waitForResponse(response => response.url().endsWith('/analysis/query'));
    await editor.press('Control+Enter');
    expect((await manual).status()).toBe(200);
    await expect(result.getByRole('columnheader', { name: /observations/ })).toBeVisible();
    await page.getByRole('button', { name: 'Visual', exact: true }).click();
    await page.getByText('Output columns', { exact: false }).click();
    await page.getByLabel('record_id', { exact: true }).check();
    await page.getByLabel('cost_chf', { exact: true }).check();
    await page.getByLabel('Row limit').fill('120');
    await page.getByRole('button', { name: 'Show generated SQL' }).click();
    await expect(page.getByLabel('Generated SQL')).toContainText('LIMIT 120');
    await waitForRun();
    await result.getByRole('button', { name: 'View lineage', exact: false }).first().click();
    await expect(result.getByText('Bronze row', { exact: false })).toBeVisible();
    await result.getByRole('button', { name: 'Next' }).click();
    await expect(result.getByText('101\u2013120 of 120')).toBeVisible();
    const csv = await page.request.get(await result.getByRole('link', { name: 'Export CSV' }).getAttribute('href').then(href => url + href));
    assert.match(await csv.text(), /^record_id,cost_chf/);
    await page.getByRole('button', { name: 'Open in SQL' }).click();
    await expect(page.getByLabel('Read-only SQL')).toHaveValue(/SELECT "record_id", "cost_chf"/);
    await expect(result.getByText('Definition changed.', { exact: false })).toBeVisible();
    await page.getByLabel('Starter investigation').selectOption({ label: 'Spending by department' });
    await waitForRun();
    await result.getByRole('button', { name: 'Chart', exact: true }).click();
    await result.getByLabel('Horizontal axis').selectOption('reporting_department');
    await result.getByLabel('Vertical axis').selectOption('recorded_cost_chf');
    await expect(result.getByRole('img', { name: 'bar chart of recorded_cost_chf' })).toBeVisible();
    if (screenshots) await page.screenshot({ path: path.join(os.tmpdir(), 'greenops-workspace-desktop.png'), fullPage: true });
    await result.getByLabel('Chart type').selectOption('line');
    await expect(result.getByRole('img', { name: 'line chart of recorded_cost_chf' })).toBeVisible();
    await result.getByLabel('Chart type').selectOption('histogram');
    await result.getByLabel('Distribution field').selectOption('recorded_cost_chf');
    await expect(result.getByRole('img', { name: 'histogram chart of recorded_cost_chf' })).toBeVisible();
    await result.getByLabel('Chart type').selectOption('scatter');
    await result.getByLabel('Horizontal axis').selectOption('recorded_rows');
    await expect(result.getByRole('img', { name: 'scatter chart of recorded_cost_chf' })).toBeVisible();
    await result.getByLabel('Chart type').selectOption('bar');

    await page.getByText('Saved analyses', { exact: true }).click();
    const name = `Workspace QA ${Date.now()}`;
    await page.getByLabel('Analysis name').fill(name);
    await page.getByRole('button', { name: 'Save definition' }).click();
    await expect(page.getByText(`Saved ${name}`, { exact: true })).toBeVisible();
    await page.reload();
    await page.getByText('Saved analyses', { exact: true }).click();
    await page.getByLabel('Open saved analysis').selectOption({ label: name });
    await expect(result).toHaveCount(0);
    await expect(page.getByLabel('Read-only SQL')).toHaveValue(/FROM cost_facts/);
    await waitForRun();
    await page.getByLabel('Read-only SQL').fill('SELECT * FROM unknown_table');
    await run();
    await expect(page.getByRole('alert')).toContainText('Query only the selected dataset');
    await expect(result.getByText('Definition changed.', { exact: false })).toBeVisible();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Delete definition' }).click();
    await expect(page.getByText('Saved definition deleted')).toBeVisible();

    const prior = await page.request.post(url + '/api/v1/analysis/saved', {
      data: { name: 'Workspace QA old version',
        definition: { version: 'prior-version', dataset: 'cost_facts', visual: { columns: ['cost_chf'], limit: 2 } } },
    });
    expect(prior.status()).toBe(201);
    const priorId = (await prior.json()).id;
    try {
      await page.reload();
      await page.getByText('Saved analyses', { exact: true }).click();
      await page.getByLabel('Open saved analysis').selectOption({ label: 'Workspace QA old version' });
      await expect(page.getByRole('button', { name: 'Run analysis' })).toBeDisabled();
      await page.getByRole('button', { name: 'Confirm rebase to current Silver' }).click();
      await waitForRun();
      await expect(result.getByText('Query limit 2 rows.')).toBeVisible();
    } finally {
      await page.request.delete(url + '/api/v1/analysis/saved/' + priorId);
    }

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await mobile.goto(url + '/analysis');
    await expect(mobile.getByRole('heading', { name: 'Analyst Workspace' })).toBeVisible();
    await expect(mobile.getByLabel('Read-only SQL')).toBeVisible();
    await mobile.locator('.workspace-query-scope summary').click();
    await expect(mobile.getByLabel('Financial eligibility')).toBeVisible();
    assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    if (screenshots) await mobile.screenshot({ path: path.join(os.tmpdir(), 'greenops-workspace-mobile.png'), fullPage: true });
    const assisted = await browser.newPage();
    const live = process.env.ANALYSIS_QA_LIVE_AI === '1';
    const question = 'How much did we spend altogether?';
    const draftSql = 'SELECT SUM(cost_chf) AS recorded_chf FROM cost_facts';
    if (!live) {
      await assisted.route('**/api/v1/analysis/catalog', async route => {
        const response = await route.fetch();
        await route.fulfill({ response, json: { ...await response.json(), ai_configured: true } });
      });
      await assisted.route('**/api/v1/analysis/draft', async route => {
        const payload = route.request().postDataJSON();
        assert.equal(payload.dataset, undefined);
        assert.equal(payload.question, question);
        await route.fulfill({ json: { dataset: 'cost_facts', sql: draftSql, explanation: 'Sums recorded CHF charges.' } });
      });
    }
    await assisted.goto(url + '/analysis');
    await assisted.getByLabel('Dataset', { exact: true }).selectOption('assets');
    await expect(assisted.getByLabel('Ask a question')).toBeVisible();
    await expect(assisted.getByRole('button', { name: 'Ask AI', exact: true })).toHaveCount(0);
    await assisted.getByLabel('Ask a question').fill(question);
    const drafting = assisted.waitForResponse(response => response.url().endsWith('/analysis/draft'), { timeout: 45_000 });
    await assisted.getByRole('button', { name: 'Draft SQL' }).click();
    const drafted = await drafting;
    assert.equal(drafted.status(), 200, await drafted.text());
    const { sql, dataset } = await drafted.json();
    assert.equal(dataset, 'cost_facts');
    await expect(assisted.getByLabel('Dataset', { exact: true })).toHaveValue('cost_facts');
    assert.ok(sql, 'Expected a SQL draft');
    await expect(assisted.getByLabel('Read-only SQL')).toHaveValue(sql);
    await expect(assisted.getByRole('region', { name: 'Analysis results' })).toHaveCount(0);
    const execution = assisted.waitForResponse(response => response.url().endsWith('/analysis/query'));
    await assisted.getByRole('button', { name: 'Run analysis' }).click();
    const executed = await execution;
    assert.equal(executed.status(), 200, await executed.text());
    await expect(assisted.getByRole('region', { name: 'Analysis results' })).toBeVisible();
    if (live) {
      const actual = await executed.json();
      const totals = actual.rows[0];
      const recon = await assisted.request.get(url + '/api/v1/silver/reconciliation?dimension=total');
      const expected = (await recon.json()).items[0].recorded_cost_chf;
      const normalize = value => String(value).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
      assert.ok(totals.some(value => normalize(value) === normalize(expected)), 'Expected the reconciled CHF subtotal');
      console.log('Live OpenAI draft reconciled to published CHF subtotal');
    }
    assert.deepEqual(errors, []);
    console.log('Desktop and mobile Silver Analyst Workspace checks passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
