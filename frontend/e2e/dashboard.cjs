/* Dashboard navigation, linked charts, case decisions and failure states. */
const { chromium, expect: playwrightExpect } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { verifyConversation, verifyRecovery } = require('./dashboard-voice.cjs');

const url = process.env.EDA_URL || 'http://127.0.0.1:8001';
const expect = playwrightExpect.configure({ timeout: 15000 });
const noOverflow = async page => {
  const overflow = await page.evaluate(() => {
    if (document.documentElement.scrollWidth <= innerWidth) return null;
    return [...document.querySelectorAll('body *')]
      .filter(element => element.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
      .slice(0, 12)
      .map(element => ({ tag: element.tagName, className: element.getAttribute('class'), right: element.getBoundingClientRect().right }));
  });
  assert.equal(overflow, null, `Dashboard overflows the viewport: ${JSON.stringify(overflow)}`);
};

async function verifyDashboard(browser, viewport, chatOnly = false) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  const requests = [];
  page.on('request', request => requests.push(new URL(request.url()).pathname));
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (['error', 'warning'].includes(message.type())) errors.push(message.text());
  });

  await page.route('**/api/v1/dashboard/chat/status', route => route.fulfill({ json: { configured: true } }));
  await page.goto(url);
  await expect(page).toHaveURL(url + '/dashboard');
  await expect(page).toHaveTitle(/GreenOps/);
  await expect(page.getByRole('navigation').getByRole('link')).toHaveText(['Data Explorer', 'Analyst Workspace', 'Dashboard', 'Recommendations']);
  await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toHaveClass('dashboard-visually-hidden');
  await expect(page.getByText('Basel sample company', { exact: true })).toHaveCount(0);
  const filters = page.getByRole('region', { name: 'Dashboard filters' });
  const baseline = page.getByRole('region', { name: 'Company-wide baseline footprint' });
  const drivers = page.getByRole('region', { name: 'Biggest drivers' });
  const trend = page.getByRole('region', { name: 'Monthly footprint' });
  const utilization = page.getByRole('region', { name: 'Utilization analysis' });
  const currentRun = await (await page.request.get(url + '/api/v1/runs/current')).json();
  const driverRow = drivers.locator('.dashboard-bars button').first();
  await expect(driverRow).toBeVisible();
  await expect(page.getByRole('region', { name: 'Calculations and downloads' })).toHaveCount(0);
  const driverName = await driverRow.locator('.dashboard-bar-name').innerText();

  let chatRequests = 0;
  await page.route('**/api/v1/dashboard/chat', async route => {
    chatRequests += 1;
    const input = route.request().postDataJSON();
    assert.equal(input.run_id, currentRun.run_id);
    assert.equal(input.filters.scenario, 'mid');
    assert.equal(input.history.length, chatRequests - 1);
    if (chatRequests === 1) assert.equal(input.question, 'Which tools cost the most?');
    if (chatRequests === 2) assert.deepEqual(input.history[0].scopes, ['Baseline']);
    await route.fulfill({ json: {
      answer: chatRequests === 1 ? 'Here is the published spending.' : 'Here is the weekly utilization.',
      verified_only: chatRequests === 2,
      sources: [chatRequests === 1 ? {
        layer: 'Gold', dataset: 'summary', scope: 'Baseline', url: '/data-explorer',
        ranking_scope: { scenario: 'mid', group: 'tool', metric: 'cost', driver: '', months: null },
        rows: [{ label: driverName, recorded_cost_chf: 40, imputed_cost_chf: 2 }],
      } : { layer: 'Silver', dataset: 'summary', scope: 'Baseline', url: '/data-explorer', rows: [{ value: 42 }] }],
    } });
  });
  const launch = page.getByRole('button', { name: 'Ask GreenOps', exact: true });
  const chat = page.getByRole('complementary', { name: 'Ask GreenOps' });
  await expect(launch).toHaveAttribute('aria-expanded', 'false');
  await expect(chat).toBeHidden();
  const dashboardBox = await filters.boundingBox();
  const chartBox = await drivers.boundingBox();
  const launchBox = await launch.boundingBox();
  const inset = viewport.width <= 600 ? 12 : 20;
  assert.equal(launchBox.x + launchBox.width, viewport.width - inset);
  assert.equal(launchBox.y + launchBox.height, viewport.height - inset);
  await launch.click();
  await expect(chat).toBeVisible();
  await expect(chat.getByRole('button', { name: 'Close chat' })).toBeFocused();
  assert.deepEqual(await filters.boundingBox(), dashboardBox);
  assert.deepEqual(await drivers.boundingBox(), chartBox);
  const chatBox = await chat.boundingBox();
  assert.equal(chatBox.x + chatBox.width, launchBox.x + launchBox.width);
  assert.ok(chatBox.y + chatBox.height <= launchBox.y + 5);
  await expect(chat.getByText(/Dashboard scope.*All months.*Spending by tool/)).toBeVisible();
  await chat.getByRole('button', { name: 'Which tools cost the most?' }).click();
  await expect(page.getByText(/Here is the published spending/)).toBeVisible();
  await expect(chat.getByText('CHF 42', { exact: true })).toBeVisible();
  await page.getByText('Gold · summary · Baseline').click();
  await expect(page.getByRole('cell', { name: '40', exact: true })).toBeVisible();
  await page.getByLabel('Your question').fill('How about weekly utilization?');
  await page.keyboard.press('Escape');
  await expect(chat).toBeHidden();
  await expect(launch).toBeFocused();
  await launch.click();
  await expect(page.getByLabel('Your question')).toHaveValue('How about weekly utilization?');
  await page.getByLabel('Your question').press('End');
  await page.getByLabel('Your question').press('Shift+Enter');
  await expect(page.getByLabel('Your question')).toHaveValue('How about weekly utilization?\n');
  await page.getByLabel('Your question').press('Enter');
  await expect(page.getByText(/Here is the weekly utilization/)).toBeVisible();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  if (viewport.width <= 600) {
    await page.setViewportSize({ width: viewport.width, height: 360 });
    await expect(chat.getByRole('button', { name: 'Send', exact: true })).toBeInViewport();
    await page.setViewportSize(viewport);
  }
  await noOverflow(page);
  await page.getByRole('button', { name: 'Show in Biggest drivers' }).click();
  await expect(chat).toBeHidden();
  await expect(driverRow).toHaveAttribute('data-chat-evidence', 'true');
  await expect(driverRow).toBeFocused();
  await launch.click();
  await page.getByRole('button', { name: 'Clear chat' }).click();
  await expect(page.getByRole('log')).toBeEmpty();
  await expect(chat.getByRole('button', { name: 'Which tools cost the most?' })).toBeVisible();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.getByRole('button', { name: 'Close chat' }).click();
  await expect(chat).toBeHidden();
  await expect(filters).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  if (chatOnly) {
    assert.deepEqual(errors, []);
    await page.close();
    return;
  }
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
  const recommendationPages = recommendations.getByRole('group', { name: 'Recommendation pages' });
  const findRecommendation = async locator => {
    const next = recommendationPages.getByRole('button', { name: 'Next' });
    await expect(recommendations.getByRole('table', { name: 'Grouped recommendations' })).toBeVisible();
    while (!(await locator.isVisible()) && await next.isVisible() && await next.isEnabled()) {
      await next.click();
    }
    await expect(locator).toBeVisible();
  };
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
  await findRecommendation(schedule);
  await expect(schedule).toContainText('Needs review', { timeout: 15000 });
  await expect(schedule).toContainText(/1[’']532\.33/);
  await expect(recommendations.getByRole('columnheader', { name: /Potential monthly savings.*Aug 2026/ })).toBeVisible();
  assert.ok(!requests.some(request => request.endsWith(`/recommendations/${developmentRecommendation.id}/evidence`)));
  await schedule.getByRole('button').click();
  const expansion = recommendations.locator('tr.dashboard-recommendation-expansion:visible');
  const clusterImpact = expansion.getByRole('region', { name: 'Monthly spending comparison' });
  await expect(clusterImpact).toContainText('Includes savings subject to review');
  await expect(clusterImpact.getByRole('group', { name: 'Monthly spending chart' })).toBeVisible();
  await expect(clusterImpact.locator('path.recharts-line-curve')).toHaveCount(3);
  await expansion.getByText('dp-dev', { exact: true }).click();
  await expansion.getByText('Recurrence source rows', { exact: true }).click();
  await expect(expansion.getByRole('listitem').filter({ hasText: /^data_platform_usage\.csv/ })).toBeVisible();
  await schedule.getByRole('button').click();
  const crmRow = recommendations.locator('tr.dashboard-recommendation').filter({ hasText: 'CRM platform' });
  await recommendations.getByLabel('Spending horizon').selectOption('year');
  await findRecommendation(crmRow);
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
  await findRecommendation(recommendations.getByRole('button', { name: /Review cluster pauses.*Data platforms/ }));
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
  const periodOptions = filters.locator('.dashboard-period-options');
  await period.click();
  await expect(page.locator('.dashboard-period input:checked')).toHaveCount(13);
  await august.uncheck();
  await expect(allMonths).not.toBeChecked();
  await periodOptions.getByText('All months', { exact: true }).click();
  await expect(page.locator('.dashboard-period input:checked')).toHaveCount(13);
  await allMonths.uncheck();
  await expect(recommendations).toContainText('Select at least one month');
  await august.check();
  await periodOptions.getByText('Jul 2026', { exact: true }).click();
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

async function verifyRecommendationSummary(browser, viewport) {
  const page = await browser.newPage({ viewport });
  const explanation = 'Unused seats recurred, so review seat counts at renewal.';
  await page.route(/\/recommendation-groups\?/, async route => {
    const response = await route.fetch();
    const rows = await response.json();
    const crm = rows.find(row => row.scope === 'CRM platform');
    if (crm) delete crm.spending_projection;
    const member = crm?.members[0];
    if (member) member.ai_tag = { decision: 'human_review', reason: 'contract', evidence_id: 'fixture', explanation };
    const blocked = rows.flatMap(row => row.members).find(item => item.resource === 'dr-failover');
    if (blocked) delete blocked.safety_reason;
    await route.fulfill({ response, json: rows });
  });
  await page.goto(url + '/recommendations');
  const summary = page.getByRole('region', { name: 'Overall summary' });
  const results = page.getByRole('region', { name: 'Recommended actions' });
  const search = page.getByRole('searchbox', { name: 'Find a recommendation' });
  await expect(summary).toBeVisible();
  await expect(summary.getByRole('article')).toHaveCount(3);
  await expect(summary.getByText(/eligible|conditional|partial coverage|show breakdown/i)).toHaveCount(0);
  const pages = results.getByRole('group', { name: 'Recommendation pages' });
  await expect(results.locator('tr.dashboard-recommendation')).toHaveCount(15);
  await expect(pages).toContainText('1–15 of');
  await pages.getByRole('button', { name: 'Next' }).click();
  await expect(pages).toContainText('16–');
  await search.fill('dr-failover');
  await page.getByRole('button', { name: /dr-failover.*Review server downsizing or pauses/ }).click();
  await expect(page.getByRole('cell', { name: 'The named disaster recovery server must remain running.' })).toBeVisible();
  await expect(page.getByText('This action is blocked.', { exact: true })).toBeVisible();
  await search.fill('Accounting software');
  await page.getByRole('button', { name: /Accounting software.*Reduce unused seats at renewal/ }).click();
  const comparison = results.getByRole('region', { name: 'Monthly spending comparison' });
  await expect(comparison).toContainText('Earliest modeled start 1 Apr 2027');
  await expect(comparison.getByRole('table')).toHaveCount(0);
  const chart = comparison.getByRole('group', { name: 'Monthly spending chart' });
  await expect(chart.locator('path.recharts-line-curve')).toHaveCount(3);
  await chart.getByRole('application').focus();
  for (let month = 0; month < 16; month++) await page.keyboard.press('ArrowRight');
  const tooltip = chart.getByRole('status');
  await expect(tooltip).toContainText('Aug 2027');
  await expect(tooltip).toContainText(/Current setup .*380\.00/);
  await expect(tooltip).toContainText(/If followed .*342\.00/);
  await expect(tooltip).toContainText(/Monthly savings .*38\.00/);
  await noOverflow(page);
  if (process.env.DASHBOARD_GROUPS_QA_DIR) {
    await comparison.screenshot({ path: path.join(process.env.DASHBOARD_GROUPS_QA_DIR, `monthly-${viewport.width}.png`) });
  }
  await search.fill('CRM platform');
  await expect(results).toContainText('1 matching recommendation');
  await expect(results).toContainText('2 supporting resources');
  await expect(summary).toContainText(/6[’']600\.00/);
  const filters = results.getByRole('button', { name: 'Filters' });
  if (await filters.isVisible()) await filters.click();
  await page.getByLabel('Savings shown').selectOption('energy');
  await expect(summary).toContainText(/6[’']600\.00/);
  await page.getByRole('button', { name: /CRM platform.*Reduce unused seats at renewal/ }).click();
  await expect(page.getByRole('cell', { name: explanation })).toBeVisible();
  const estimated = results.getByRole('region', { name: 'Estimated spending impact' });
  await expect(estimated).toContainText('Includes savings subject to review');
  await expect(estimated).toContainText('550.00 / month');
  await expect(estimated).toContainText(/6[’']600\.00 annualized savings/);
  await expect(estimated).toContainText('27 seats');
  await expect(estimated).toContainText('17 seats');
  await expect(estimated).toContainText(/1[’']485\.00/);
  await expect(estimated).toContainText('935.00');
  await expect(estimated).toContainText('1 Nov 2026 notice deadline had passed');
  await expect(estimated.getByRole('img')).toHaveCount(0);
  await expect(estimated.getByRole('table')).toHaveCount(0);
  await noOverflow(page);
  if (process.env.DASHBOARD_GROUPS_QA_DIR) {
    await estimated.screenshot({ path: path.join(process.env.DASHBOARD_GROUPS_QA_DIR, `impact-${viewport.width}.png`) });
  }
  await page.getByLabel('Resource type').selectOption('shutdown');
  await expect(results).toContainText('0 matching recommendations');
  await expect(summary).toContainText('Unavailable');
  await results.getByRole('button', { name: 'Clear filters' }).click();
  await expect(pages).toContainText('1–15 of');
  await page.getByLabel('Group by').selectOption('platform');
  await expect(results.getByRole('columnheader', { name: 'Platform / recommended action' })).toBeAttached();
  await page.getByRole('radio', { name: /^high$/i }).check();
  await expect(results.getByRole('table', { name: 'Recommendations for underused resources' })).toBeVisible();
  await page.unrouteAll({ behavior: 'wait' });
  await page.close();
}

async function verifyUnavailable(browser) {
  const page = await browser.newPage();
  const current = '**/api/v1/runs/current';
  let currentUnavailable = true;
  let breakdownUnavailable = true;
  await page.route(current, route => currentUnavailable ? route.fulfill({
    status: 503,
    json: { detail: { message: 'A validated Gold run is unavailable.' } },
  }) : route.continue());
  await page.route(/\/api\/v1\/runs\/[^/]+\/breakdowns\?/, route => breakdownUnavailable ? route.fulfill({
    status: 503,
    json: { detail: { message: 'Breakdown unavailable.' } },
  }) : route.continue());
  await page.goto(url + '/dashboard');
  await expect(page.getByRole('alert')).toContainText('A validated Gold run is unavailable.');
  currentUnavailable = false;
  await page.getByRole('button', { name: 'Retry published data' }).click();
  const trend = page.getByRole('region', { name: 'Monthly footprint' });
  await expect(trend.getByRole('alert')).toContainText('Breakdown unavailable.');
  await expect(page.getByRole('region', { name: 'Utilization analysis' })).toBeVisible();
  breakdownUnavailable = false;
  await trend.getByRole('button', { name: 'Retry monthly data' }).click();
  await expect(trend.getByRole('img', { name: /Monthly Spending for the company/ })).toBeVisible();
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [{ width: 1568, height: 1003 }, { width: 390, height: 844 }]) {
      if (process.argv.includes('--voice-only')) {
        await verifyConversation(browser, url, viewport);
        console.log(`Hands-free Dashboard chat passed at ${viewport.width} × ${viewport.height}.`);
        continue;
      }
      if (process.argv.includes('--chat-only')) {
        await verifyDashboard(browser, viewport, true);
        console.log(`Dashboard chat passed at ${viewport.width} × ${viewport.height}.`);
        continue;
      }
      await verifyRecommendationSummary(browser, viewport);
      console.log(`Recommendations passed at ${viewport.width} × ${viewport.height}.`);
      if (process.argv.includes('--recommendations-only')) continue;
      await verifyDashboard(browser, viewport);
      console.log(`Dashboard passed at ${viewport.width} × ${viewport.height}.`);
    }
    if (process.argv.includes('--voice-only')) {
      await verifyRecovery(browser, url);
      console.log('Dashboard voice recovery and cleanup passed.');
    } else if (!process.argv.includes('--chat-only') && !process.argv.includes('--recommendations-only')) {
      await verifyUnavailable(browser);
      console.log('Dashboard availability and retry checks passed.');
      for (const viewport of [{ width: 1568, height: 1003 }, { width: 390, height: 844 }]) {
        await verifyConversation(browser, url, viewport);
        console.log(`Hands-free Dashboard chat passed at ${viewport.width} × ${viewport.height}.`);
      }
      await verifyRecovery(browser, url);
      console.log('Dashboard voice recovery and cleanup passed.');
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
