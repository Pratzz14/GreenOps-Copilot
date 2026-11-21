/* Dashboard navigation, linked charts, case decisions and failure states. */
const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');

const url = process.env.EDA_URL || 'http://127.0.0.1:8001';
const noOverflow = async page => {
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Dashboard overflows the viewport');
};

async function verifyDashboard(browser, viewport) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  const requests = [];
  page.on('request', request => requests.push(new URL(request.url()).pathname));
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (['error', 'warning'].includes(message.type())) errors.push(message.text());
  });

  await page.goto(url);
  await expect(page).toHaveURL(url + '/dashboard');
  await expect(page).toHaveTitle(/GreenOps/);
  await expect(page.getByRole('navigation').getByRole('link')).toHaveText(['Data Explorer', 'Analyst Workspace', 'Dashboard']);
  await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toHaveClass('dashboard-visually-hidden');
  await expect(page.getByText('Basel sample company', { exact: true })).toHaveCount(0);
  const filters = page.getByRole('region', { name: 'Dashboard filters' });
  const baseline = page.getByRole('region', { name: 'Company-wide baseline footprint' });
  const drivers = page.getByRole('region', { name: 'Biggest drivers' });
  const trend = page.getByRole('region', { name: 'Monthly footprint' });
  const utilization = page.getByRole('region', { name: 'Utilization analysis' });
  const currentRun = await (await page.request.get(url + '/api/v1/runs/current')).json();
  const recommendationUrl = url + `/api/v1/runs/${currentRun.run_id}/recommendations`;
  const response = await page.request.get(recommendationUrl);
  assert.ok(response.ok(), 'Recommendations API should return the published catalog');
  const catalog = await response.json();
  const developmentRecommendation = catalog.find(item => item.resource === 'dp-dev');
  assert.equal(developmentRecommendation.safety_status, 'human_review');
  assert.equal(catalog.find(item => item.resource === 'dr-failover').safety_status, 'blocked');
  const projected = await (await page.request.get(recommendationUrl + '?months=2025-10&months=2026-07&group=provider&driver=Azure')).json();
  assert.deepEqual(projected.find(item => item.id === developmentRecommendation.id).estimate, developmentRecommendation.estimate);
  const recommendations = page.getByRole('region', { name: 'Recommendations' });
  const groupedUrl = recommendationUrl.replace(/recommendations$/, 'recommendation-groups');
  const july = await (await page.request.get(groupedUrl +
    '?group=tool&driver=Microsoft%20Copilot&months=2026-06&months=2026-07')).json();
  assert.equal(july[0].display_month, '2026-07');
  assert.deepEqual(Object.keys(july[0].monthly_spend), ['2026-06', '2026-07']);
  assert.equal(Number(july[0].monthly_spend['2026-07'].conditional).toFixed(2), '680.99');
  for (const group of ['tool', 'platform', 'provider', 'location', 'department']) {
    const grouped = await (await page.request.get(groupedUrl + '?group=' + group)).json();
    assert.ok(grouped.length < catalog.length);
    const ids = grouped.flatMap(row => row.members.map(member => member.id));
    assert.deepEqual(ids.sort(), catalog.map(row => row.id).sort());
    if (group === 'tool') {
      const crm = grouped.find(row => row.scope === 'CRM platform');
      assert.equal(crm.members.length, 2);
      assert.equal(crm.persistent_unused, 10);
      assert.equal(Number(crm.savings.steady_state.net_chf.conditional), 6600);
      const copilot = grouped.find(row => row.scope === 'Microsoft Copilot');
      assert.equal(copilot.display_month, '2026-08');
      assert.equal(Number(copilot.monthly_spend['2026-08'].conditional).toFixed(2), '678.38');
      assert.equal(Number(copilot.savings.steady_state.net_chf.conditional).toFixed(2), '7733.58');
      assert.equal(copilot.savings.steady_state.savings_kwh.conditional, null);
    }
  }
  const schedule = recommendations.locator('tr.dashboard-recommendation').filter({ hasText: 'Data platform development' });
  await expect(schedule).toContainText('Needs review', { timeout: 15000 });
  await expect(schedule).toContainText(/1[’']532\.33/);
  await expect(recommendations.getByRole('columnheader', { name: /Potential monthly savings.*Aug 2026/ })).toBeVisible();
  assert.ok(!requests.some(request => request.endsWith(`/recommendations/${developmentRecommendation.id}/evidence`)));
  await schedule.getByRole('button').click();
  const expansion = recommendations.locator('tr.dashboard-recommendation-expansion:visible');
  await expansion.getByText('dp-dev', { exact: true }).click();
  await expansion.getByText('Recurrence source rows', { exact: true }).click();
  await expect(expansion.getByRole('listitem').filter({ hasText: /^data_platform_usage\.csv/ })).toBeVisible();
  await schedule.getByRole('button').click();
  const crmRow = recommendations.locator('tr.dashboard-recommendation').filter({ hasText: 'CRM platform' });
  await recommendations.getByLabel('Spending horizon').selectOption('year');
  await expect(crmRow).toContainText('10 unused seats');
  await crmRow.getByRole('button').click();
  await expect(expansion.getByText(/CRM platform.*4100/)).toBeVisible();
  assert.ok(await expansion.getByRole('table', { name: 'Supporting scopes' }).evaluate(table => {
    const edge = table.getBoundingClientRect().right;
    return [...table.querySelectorAll('tbody td')].every(cell => cell.getBoundingClientRect().right <= edge + 1);
  }), 'Supporting scopes should fit inside the evidence panel');
  if (process.env.DASHBOARD_GROUPS_QA_DIR) {
    await recommendations.screenshot({ path: path.join(process.env.DASHBOARD_GROUPS_QA_DIR, `groups-${viewport.width}.png`) });
  }
  await crmRow.getByRole('button').click();
  await recommendations.getByLabel('Spending horizon').selectOption('month');
  await utilization.getByRole('searchbox').fill('dp-dev');
  await utilization.getByRole('button', { name: /dp-dev/ }).click();
  await utilization.getByRole('link', { name: 'View recommendation' }).click();
  await expect(expansion.locator('[data-selected="true"]')).toContainText('dp-dev');
  await schedule.getByRole('button').click();
  await utilization.getByRole('searchbox').fill('');
  await page.evaluate(() => window.history.replaceState(null, '', window.location.pathname));
  await filters.getByLabel('Group by').selectOption('platform');
  await expect(recommendations).toContainText('Grouped by platform');
  await expect(drivers.getByRole('list', { name: 'Ranked platform drivers' })).toBeVisible();
  await expect(recommendations.getByRole('button', { name: /Review cluster pauses.*Data platforms/ })).toBeVisible();
  await filters.getByLabel('Group by').selectOption('tool');
  const overview = await (await page.request.get(url + `/api/v1/runs/${currentRun.run_id}/overview`)).json();
  assert.ok(Number(overview.imputed_cost_chf) > 0, 'Gold run must include imputed charges');
  const estimatedSpending = await page.evaluate(amount => {
    const chf = new Intl.NumberFormat('en-CH', { style: 'currency', currency: 'CHF' });
    return chf.format(amount);
  }, Number(overview.cost.value) + Number(overview.imputed_cost_chf));
  const emissionsTotal = body => `${(Number(body.reporting_kg_co2e) / 1000).toFixed(2)} t CO₂e`;
  assert.equal(emissionsTotal(overview), '18.13 t CO₂e');
  await expect(baseline).toContainText(emissionsTotal(overview), { timeout: 15000 });
  await expect(baseline.locator('.dashboard-kpis > div')).toHaveCount(3);
  await expect(baseline).toContainText(/128[,'’]061 kWh/);
  await expect(baseline).toContainText(estimatedSpending);
  await expect(baseline.getByText(/Includes CHF .* imputed/)).toHaveCount(0);
  await expect(baseline.getByText('Partial coverage', { exact: true })).toHaveCount(2);
  const emissionsCard = baseline.locator('.dashboard-kpis > div').filter({ hasText: 'Estimated emissions' });
  await expect(emissionsCard.locator('.dashboard-coverage')).toHaveText('Partial coverage');
  await expect(page.getByRole('region', { name: 'Electricity and emissions coverage' })).toHaveCount(0);
  const spendingCard = baseline.locator('.dashboard-kpis > div').filter({ hasText: 'Estimated spending' });
  await expect(spendingCard.locator('.dashboard-coverage')).toHaveCount(0);
  await expect(recommendations).toBeVisible();
  await expect(page.getByLabel('Metric', { exact: true })).toHaveValue('cost');
  await expect(trend.getByRole('img', { name: /Monthly Spending for the company/ })).toBeVisible();
  assert.ok(!requests.some(request => request.includes('/evidence/') || request.endsWith('/factors')));
  const sortByCost = (a, b) => b.cost - a.cost || a.name.localeCompare(b.name);
  const breakdown = await (await page.request.get(url + `/api/v1/runs/${currentRun.run_id}/breakdowns?group=tool`)).json();
  const rankedDrivers = breakdown.filter(row => row.report_month === null)
    .map(row => ({ name: row.driver, cost: Number(row.recorded_cost_chf) + Number(row.imputed_cost_chf) }))
    .sort(sortByCost);
  const driverNames = drivers.getByRole('list', { name: 'Ranked tool drivers' }).locator('.dashboard-bar-name');
  const driverPages = drivers.getByRole('group', { name: 'Driver pages' });
  await expect(driverNames).toHaveText(rankedDrivers.slice(0, 10).map(row => row.name));
  await driverPages.getByRole('button', { name: 'Next' }).click();
  await expect(driverNames).toHaveText(rankedDrivers.slice(10, 20).map(row => row.name));
  await driverPages.getByRole('button', { name: 'Previous' }).click();
  await expect(driverNames).toHaveText(rankedDrivers.slice(0, 10).map(row => row.name));

  const scan = await (await page.request.get(url + `/api/v1/runs/${currentRun.run_id}/utilization?include_estimates=true`)).json();
  const rankedResources = scan.items
    .map(row => ({ name: row.resource, cost: Number(row.impact.cost ?? -Infinity) })).sort(sortByCost);
  const utilizationTable = utilization.getByRole('table', { name: 'Resource utilization and impact' });
  await expect(utilization.getByRole('combobox')).toHaveCount(0);
  await expect(utilization.getByRole('searchbox', { name: 'Find a resource' })).toBeVisible();
  await expect(utilizationTable.getByRole('columnheader', { name: 'Spending' })).toHaveAttribute('aria-sort', 'descending');
  const resourceNames = utilizationTable.locator('.dashboard-utilization-resource strong');
  await expect(resourceNames).toHaveText(rankedResources.slice(0, 5).map(row => row.name));
  await expect(utilization.getByText(/Assess resizing or scheduled pauses|Review reducing seats at renewal/)).toHaveCount(0);
  const resourcePages = utilization.getByRole('group', { name: 'Resource pages' });
  await expect(resourcePages).toContainText(`1–5 of ${rankedResources.length}`);
  await resourcePages.getByRole('button', { name: 'Next' }).click();
  await expect(resourceNames).toHaveText(rankedResources.slice(5, 10).map(row => row.name));
  await expect(resourcePages).toContainText(`6–10 of ${rankedResources.length}`);
  await resourcePages.getByRole('button', { name: 'Previous' }).click();
  await expect(resourceNames).toHaveText(rankedResources.slice(0, 5).map(row => row.name));
  await resourcePages.getByRole('button', { name: 'Next' }).click();
  for (const [metric, label] of [['energy', 'Energy'], ['carbon', 'Emissions'], ['cost', 'Spending']]) {
    const column = utilizationTable.getByRole('columnheader', { name: label, exact: true });
    const button = column.getByRole('button');
    if (metric === 'energy') await button.click();
    else await button.press('Enter');
    await expect(button).toBeFocused();
    await expect(column).toHaveAttribute('aria-sort', 'descending');
    await expect(resourcePages).toContainText(`1–5 of ${rankedResources.length}`);
    const ranked = scan.items.map(row => ({ name: row.resource, cost: Number(row.impact[metric] ?? -Infinity) }))
      .sort(sortByCost);
    await expect(resourceNames).toHaveText(ranked.slice(0, 5).map(row => row.name));
  }
  await noOverflow(page);
  if (process.env.DASHBOARD_QA_DIR) {
    const file = path.join(process.env.DASHBOARD_QA_DIR, `greenops-dashboard-${viewport.width}.png`);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: file, fullPage: viewport.width < 730 });
  }

  await page.evaluate(() => window.scrollTo(0, 650));
  await expect.poll(() => filters.evaluate(element => element.getBoundingClientRect().top)).toBe(0);
  await filters.getByLabel('Metric', { exact: true }).selectOption('energy');
  await expect(trend.getByRole('img', { name: /Monthly Energy for the company/ })).toBeVisible();
  const period = filters.locator('.dashboard-period > summary');
  await period.click();
  await expect(filters.getByRole('checkbox', { name: 'All months', exact: true })).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(200);
  if (process.env.DASHBOARD_QA_DIR) {
    await page.screenshot({ path: path.join(process.env.DASHBOARD_QA_DIR, `sticky-filters-${viewport.width}.png`) });
  }
  await period.press('Escape');

  await page.getByLabel('Metric', { exact: true }).selectOption('carbon');
  const development = drivers.getByRole('button', { name: /Data platform development/ });
  await development.press('Enter');
  await expect(development).toHaveAttribute('aria-pressed', 'true');
  await expect(utilization.locator('.dashboard-utilization-row')).toHaveCount(1, { timeout: 15000 });
  await expect(trend.getByRole('img', { name: /Monthly Emissions for Data platform development/i })).toBeVisible();
  const allMonths = page.getByRole('checkbox', { name: 'All months', exact: true });
  const august = page.getByRole('checkbox', { name: 'Aug 2026' });
  await period.click();
  await expect(page.locator('.dashboard-period input:checked')).toHaveCount(13);
  await august.uncheck();
  await expect(allMonths).not.toBeChecked();
  await allMonths.check();
  await expect(page.locator('.dashboard-period input:checked')).toHaveCount(13);
  await allMonths.uncheck();
  await expect(recommendations).toContainText('Select at least one month');
  await august.check();
  await page.getByRole('checkbox', { name: 'Jul 2026' }).check();
  await expect(period).toHaveText('2 months selected');
  await expect(utilization).toContainText('2 months selected');
  await august.press('Escape');
  await trend.getByText('View monthly data', { exact: true }).click();
  await expect(trend.getByRole('rowheader')).toHaveText(['Jul 2026', 'Aug 2026']);
  await trend.getByText('View monthly data', { exact: true }).click();
  await period.click();
  await page.getByRole('checkbox', { name: 'Jul 2026' }).uncheck();
  await august.press('Escape');
  await expect(trend).toContainText('Aug 2026');
  await expect(development).not.toContainText('10.75 t CO₂');
  await expect(baseline).toContainText(emissionsTotal(overview));
  await trend.getByRole('button', { name: 'Clear driver' }).click();
  await expect(development).toHaveAttribute('aria-pressed', 'false');
  await page.getByLabel('Group by').selectOption('department');
  await page.getByLabel('Metric', { exact: true }).selectOption('cost');
  await expect(drivers.getByRole('button', { name: /^IT.*CHF/ })).toBeVisible({ timeout: 15000 });
  await page.getByLabel('Group by').selectOption('provider');
  await expect(drivers.getByRole('list', { name: 'Ranked provider drivers' })).toBeVisible({ timeout: 15000 });
  const info = baseline.getByRole('button', { name: 'About Estimated spending' });
  for (const trigger of await baseline.getByRole('button', { name: /^About / }).all()) {
    await trigger.hover();
    const panel = trigger.locator('..').locator('.dashboard-info-content');
    await expect(panel).toBeVisible();
    const anchor = await trigger.boundingBox();
    const popup = await panel.boundingBox();
    assert.ok(popup.x <= anchor.x + 1 && popup.x + popup.width >= anchor.x + anchor.width - 1);
    assert.ok(Math.min(Math.abs(popup.y - anchor.y - anchor.height),
      Math.abs(popup.y + popup.height - anchor.y)) <= 1, 'Info panel should touch its trigger');
    assert.ok(popup.x >= 0 && popup.x + popup.width <= viewport.width);
    assert.ok(popup.y >= 0 && popup.y + popup.height <= viewport.height);
    await panel.hover();
    await expect(panel).toBeVisible();
    await page.mouse.move(0, 0);
    await expect(panel).toBeHidden();
  }
  await info.focus();
  await expect(info).toHaveAttribute('aria-expanded', 'true');
  await expect(baseline.getByText(/Recorded spending CHF/)).toBeVisible();
  await baseline.getByText('Billing coverage details', { exact: true }).click();
  await expect(baseline.getByText(/missing exchange rates/)).toBeVisible();
  await info.press('Escape');
  await expect(info).toHaveAttribute('aria-expanded', 'false');
  await page.getByLabel('Group by').selectOption('location');
  await page.getByLabel('Metric', { exact: true }).selectOption('carbon');
  await expect(drivers.getByRole('list', { name: 'Ranked location drivers' })).toBeVisible({ timeout: 15000 });
  await expect(drivers.getByRole('list').getByRole('button', { name: /Switzerland/ })).toBeVisible();
  await drivers.getByText('View breakdown', { exact: true }).click();
  const swiss = drivers.getByRole('row').filter({ hasText: 'Switzerland' });
  await expect(swiss).toContainText('0.37 t CO₂e');
  await period.click();
  await allMonths.check();
  await allMonths.press('Escape');
  await expect(swiss).toContainText('3.96 t CO₂e');
  await expect(drivers.getByRole('columnheader', { name: 'Imputed spending' })).toBeVisible();
  await drivers.getByText('View breakdown', { exact: true }).click();
  await page.getByLabel('Assumptions').selectOption('low');
  const low = await (await page.request.get(url + `/api/v1/runs/${currentRun.run_id}/overview?scenario=low`)).json();
  await expect(baseline).toContainText(emissionsTotal(low));
  await expect(baseline).toContainText(estimatedSpending);
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await expect(page.getByLabel('Assumptions')).toHaveValue('mid');
  await expect(page.getByLabel('Metric', { exact: true })).toHaveValue('cost');
  await page.getByLabel('Metric', { exact: true }).selectOption('carbon');
  await expect(drivers.getByRole('button', { name: /Data platform development.*10.75/ })).toBeVisible();

  await page.getByLabel('Metric', { exact: true }).selectOption('energy');
  await drivers.getByText('View breakdown', { exact: true }).click();
  const production = drivers.getByRole('row').filter({ hasText: 'Data platform production' });
  await expect(production).toContainText('3.71 t CO₂e');
  await production.getByRole('button').press('Enter');
  await page.getByLabel('Metric', { exact: true }).selectOption('carbon');
  await expect(trend.getByRole('img', { name: /Monthly Emissions for Data platform production/i })).toBeVisible();
  await trend.getByText('View monthly data', { exact: true }).click();
  await expect(trend.getByRole('rowheader')).toHaveCount(12);
  await expect(trend.getByRole('table').getByText('Unavailable', { exact: true })).toHaveCount(0);
  await noOverflow(page);

  const emissionsInfo = baseline.getByRole('button', { name: 'About Estimated emissions' });
  await emissionsInfo.click();
  const emissionsPanel = emissionsInfo.locator('..').locator('.dashboard-info-content');
  await expect.poll(async () => {
    const panel = await emissionsPanel.boundingBox();
    const filterBar = await filters.boundingBox();
    return panel && filterBar && panel.y >= filterBar.y + filterBar.height - 1;
  }).toBe(true);
  await expect(baseline.getByText('Swiss consumption electricity including imports, operating emissions')).toBeVisible({ timeout: 20000 });
  await baseline.getByText('Sources and coverage', { exact: true }).click();
  await expect(baseline.locator('.gold-evidence ul').first()).toBeVisible();
  await emissionsInfo.press('Escape');
  await page.getByRole('button', { name: 'Reset filters' }).click();
  const search = utilization.getByRole('searchbox');
  await search.fill('dp-dev');
  const cluster = utilization.locator('.dashboard-utilization-row');
  await expect(cluster).toHaveCount(1);
  const resourceButton = cluster.getByRole('button', { name: /dp-dev/ });
  await resourceButton.press('Enter');
  await expect(resourceButton).toHaveAttribute('aria-expanded', 'true');
  const evidence = utilization.locator('.dashboard-utilization-evidence');
  await expect(evidence).toContainText('at most 20% active');
  await evidence.getByText('Source rows', { exact: true }).click();
  await expect(evidence.getByText(/data_platform_usage.csv/)).toBeVisible();
  await resourceButton.click();
  await expect(evidence).toBeHidden();
  await search.fill('nonexistent-resource');
  await expect(utilization).toContainText('No resources match your search.');
  const files = [
    ['Draft baseline CSV', 'parameter,must_or_bonus,value_low,value_mid,value_high,unit,source,calculation_or_assumption'],
    ['Provisional submission measures CSV', 'measure_id,description,resource_or_source,change,effort_person_days'],
    ['Conditional draft measures CSV', 'measure_id,description,resource_or_source,change,effort_person_days'],
  ];
  for (const [name, header] of files) {
    const download = page.waitForEvent('download');
    const link = page.getByRole('link', { name, exact: true });
    await link.click();
    assert.match((await download).suggestedFilename(), /^(draft-conditional-)?template_/);
    const response = await page.request.get(url + await link.getAttribute('href'));
    assert.ok((await response.text()).replace(/^\uFEFF/, '').startsWith(header));
  }
  await noOverflow(page);
  await page.reload();
  await expect(baseline).toContainText('18.13 t CO₂e');
  await page.getByRole('link', { name: 'Data Explorer' }).click();
  await expect(page.getByRole('heading', { name: 'Data journey', exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Bronze', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Bronze overview' })).toBeVisible();
  await page.getByRole('link', { name: 'Analyst Workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Analyst Workspace', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'GreenOps Copilot' }).click();
  await expect(page).toHaveURL(url + '/dashboard');
  assert.deepEqual(errors, []);
  await page.close();
}

async function verifyUnavailable(browser) {
  const page = await browser.newPage();
  const current = '**/api/v1/runs/current';
  await page.route(current, route => route.fulfill({
    status: 503,
    json: { detail: { message: 'A validated Gold run is unavailable.' } },
  }), { times: 1 });
  await page.route(/\/api\/v1\/runs\/[^/]+\/breakdowns\?/, route => route.fulfill({
    status: 503,
    json: { detail: { message: 'Breakdown unavailable.' } },
  }), { times: 1 });
  await page.goto(url + '/dashboard');
  await expect(page.getByRole('alert')).toContainText('A validated Gold run is unavailable.');
  await page.getByRole('button', { name: 'Retry published data' }).click();
  const trend = page.getByRole('region', { name: 'Monthly footprint' });
  await expect(trend.getByRole('alert')).toContainText('Breakdown unavailable.');
  await expect(page.getByRole('region', { name: 'Utilization analysis' })).toBeVisible();
  await trend.getByRole('button', { name: 'Retry monthly data' }).click();
  await expect(trend.getByRole('img', { name: /Monthly Spending for the company/ })).toBeVisible();
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [{ width: 1568, height: 1003 }, { width: 390, height: 844 }]) {
      await verifyDashboard(browser, viewport);
      console.log(`Dashboard passed at ${viewport.width} × ${viewport.height}.`);
    }
    await verifyUnavailable(browser);
    console.log('Dashboard availability and retry checks passed.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
