import { CatalogRow } from './LayerOverview';
import type { QualityOverview } from './api/quality';

type SourceDescription = {
  file: `${string}.csv`;
  row: string;
  relevance: string;
};

const sourceCatalog = [
  { file: 'azure_costs.csv', row: 'An Azure billing line for a resource and day.', relevance: 'Shows cloud usage, charges and credits in the billed currency.' },
  { file: 'aws_costs.csv', row: 'An AWS billing line for a resource and day.', relevance: 'Shows USD usage charges and fees, including support.' },
  { file: 'hoster_invoice.csv', row: 'A daily invoice line from the Swiss hosting provider.', relevance: 'Shows CHF charges for hosting, storage and related services.' },
  { file: 'server_inventory.csv', row: 'A virtual server in the inventory snapshot.', relevance: 'Identifies assets, capacity, owners and recent activity.' },
  { file: 'server_metrics_weekly.csv', row: 'A week of monitoring for one server.', relevance: 'Shows CPU, memory, network and uptime patterns, plus GPU use where applicable.' },
  { file: 'data_platform_usage.csv', row: 'One day of activity for a data platform cluster.', relevance: 'Shows when clusters were running and how much of that time they were actively used.' },
  { file: 'ai_usage.csv', row: 'A day of AI requests grouped by tool, department, task and model.', relevance: 'Shows who uses AI, for what tasks, and at what request and token volumes.' },
  { file: 'ai_subscriptions.csv', row: 'A monthly AI subscription entry for a product and cost center.', relevance: 'Shows subscription costs, license use and draft or final status.' },
  { file: 'saas_contracts.csv', row: 'A monthly software contract entry for a cost center.', relevance: 'Shows license costs and terms that affect when subscriptions can change.' },
  { file: 'mapping_departments_tools.csv', row: 'An ownership reference for a resource.', relevance: 'Connects resources to tools, cost centers and departments where recorded.' },
  { file: 'exchange_rates.csv', row: 'One month of average EUR-to-CHF and USD-to-CHF rates.', relevance: 'Provides rates for comparing costs in CHF.' },
  { file: 'it_tickets.csv', row: 'An IT service ticket.', relevance: 'Records incidents, maintenance and other operational constraints that can affect changes.' },
  { file: 'business_calendar.csv', row: 'A calendar day with workday and holiday information.', relevance: 'Helps identify when work schedules and holidays may restrict changes.' },
] as const satisfies readonly SourceDescription[];

export function SourceCatalog({ sources }: { sources: QualityOverview['sources'] }) {
  const profiles = new Map(sources.map(source => [source.name, source]));
  return (
    <section id="catalog" aria-label="Source catalog">
      <ul className="layer-catalog">
        {sourceCatalog.map(({ file, row, relevance }) => {
          const profile = profiles.get(file);
          const issues = Object.entries(profile?.issue_counts ?? {});
          return (
            <CatalogRow key={file} name={file}
              records={profile ? `${profile.rows.toLocaleString('en-US')} records` : 'Count unavailable'}
              findings={profile ? (issues.length ? `${issues.length} issue types` : 'No issues flagged') : 'Issues unavailable'}>
              <p>{row} {relevance}</p>
              <h3>Issues found</h3>
              {issues.length ? <dl className="catalog-findings">
                {issues.map(([category, count]) => <div key={category}>
                  <dt>{category.replaceAll('_', ' ')}</dt><dd>{count.toLocaleString('en-US')}</dd>
                </div>)}
              </dl> : <p>{profile ? 'No issues flagged.' : 'Source issue counts are unavailable.'}</p>}
            </CatalogRow>
          );
        })}
      </ul>
    </section>
  );
}
