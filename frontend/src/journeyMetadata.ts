export const tableCreation: Partial<Record<string, { reason: string; method: string; inputs: string[] }>> = {
  cost_facts: {
    reason: 'Brings provider charges, gateway costs and contract amounts together for a reconciled CHF subtotal.',
    method: 'Appended one row per source charge, used monthly exchange rates for foreign amounts, and recorded each row’s baseline eligibility.',
    inputs: ['azure_costs', 'aws_costs', 'hoster_invoice', 'ai_usage', 'ai_subscriptions', 'saas_contracts', 'exchange_rates'],
  },
  usage_facts: {
    reason: 'Brings platform activity, weekly server readings and AI usage into one table so they can be explored together.',
    method: 'Appended observations from the three inputs, selected the usage fields, and labeled each row with its usage type and source record.',
    inputs: ['data_platform_usage', 'server_metrics_weekly', 'ai_usage'],
  },
  assets: {
    reason: 'Provides a shared server inventory reference for linking usage and billing records to assets.',
    method: 'Published the cleaned inventory rows as the asset reference, carrying over the snapshot date and available ownership evidence.',
    inputs: ['server_inventory'],
  },
  contracts: {
    reason: 'Puts AI and SaaS contracts side by side for monthly comparison.',
    method: 'Appended contract rows from both inputs, keeping the reporting month and the Draft or Final status of each version.',
    inputs: ['ai_subscriptions', 'saas_contracts'],
  },
  ownership: {
    reason: 'Provides a shared reference for linking resources and cost centers to departments.',
    method: 'Used unambiguous resource mappings to create resource ownership rows and one row per distinct cost-center and department pair. Kept ambiguous or unresolved ownership visible.',
    inputs: ['mapping_departments_tools'],
  },
  resource_relationships: {
    reason: 'Shows how billed resources relate to inventory assets and how strong the supporting evidence is.',
    method: 'Compared billed resource IDs with server IDs and billing providers with inventory providers. Used ownership mappings as supporting evidence and kept candidate links and unresolved pools visible.',
    inputs: ['azure_costs', 'aws_costs', 'hoster_invoice', 'server_inventory', 'mapping_departments_tools'],
  },
};

export const purpose: Record<string, string> = {
  analysis_run: 'Baseline dates, calculation versions, coverage, and targets for this run.',
  subject: 'Resources, products, and services linked to the Gold results.',
  cost_monthly: 'Recorded CHF and coverage counts by month, resource, department, tool, location, and billing stream.',
  impact_monthly: 'Estimated electricity and location-based emissions by month, workload, and scenario.',
  factor: 'Factor values, units, ranges, and sources used in this run.',
  licence_monthly: 'Final monthly contract observations, seat usage, unit prices, and notice terms.',
  finding: 'Observed waste and the evidence behind each hypothesis.',
  protection_window: 'Dated and standing restrictions on actions. Timestamps are shown in UTC.',
  measure: 'Proposed changes, effort, effective dates, and safety decisions.',
  measure_scenario: 'Measure estimates for each assumption scenario and savings horizon.',
  measure_constraint: 'Requirements, exclusions, and overlapping savings between measures.',
  package_result: 'Baseline, savings, implementation cost, and assessment status by package and scenario.',
  package_member: 'Measures and their credited contributions within each package. Conditional rows are identified by their package ID.',
  evidence: 'Source rows, ticket text, factors, and calculation notes linked from Gold results.',
};
