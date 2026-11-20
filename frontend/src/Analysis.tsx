import {lazy,Suspense,useState,type ReactNode} from 'react';

import {useQuery} from '@tanstack/react-query';

import {readQuality,type QualityOverview,type SourceDetail,type IssuePage,type Scope} from './api/quality';

const Chart=lazy(()=>import('./AnalysisChart'));

const fmt=(n:number)=>n.toLocaleString('en-US');

const human=(s:string)=>s.replaceAll('_',' ');

const short=(s:string)=>human(s.replace('.csv','')).replace('departments tools','ownership map').replace('metrics weekly','weekly metrics');

function ErrorPanel({message,retry}:{message:string;retry:()=>void}){return <div className="error-panel" role="alert"><strong>Analysis unavailable</strong><p>{message}</p><button onClick={retry}>Try again</button></div>;}

function Table({children}:{children:ReactNode}){return <div className="table-scroll" tabIndex={0}><table>{children}</table></div>;}

function Plot({children}:{children:ReactNode}){return <Suspense fallback={<p>Loading chart…</p>}>{children}</Suspense>;}

export default function Analysis(){

 const [scope,setScope]=useState<Scope>('full');const [search,setSearch]=useState('');const [role,setRole]=useState('');const [category,setCategory]=useState('');const [sort,setSort]=useState('name');const [selected,setSelected]=useState('azure_costs.csv');const [tab,setTab]=useState('columns');const [metric,setMetric]=useState('');const [unit,setUnit]=useState('');const [issueCode,setIssueCode]=useState('');const [offset,setOffset]=useState(0);

 const overview=useQuery({queryKey:['quality',scope],queryFn:({signal})=>readQuality<QualityOverview>(`?scope=${scope}`,signal)});

 const reportId=overview.data?.report_id;

 const detail=useQuery({queryKey:['quality-source',reportId,selected,scope],enabled:!!reportId,queryFn:async({signal})=>{const v=await readQuality<SourceDetail>(`/sources/${selected}?scope=${scope}`,signal);if(v.report_id!==reportId)throw Error('The report changed. Reload this page.');return v;}});

 const issues=useQuery({queryKey:['quality-issues',reportId,selected,scope,issueCode,offset],enabled:!!reportId&&tab==='issues',queryFn:async({signal})=>{const v=await readQuality<IssuePage>(`/sources/${selected}/issues?scope=${scope}&offset=${offset}&limit=10${issueCode?`&code=${issueCode}`:''}`,signal);if(v.report_id!==reportId)throw Error('The report changed. Reload this page.');return v;}});

 function selectSource(name:string){setSelected(name);setMetric('');setIssueCode('');setOffset(0);setTab('columns');}

 if(overview.isPending)return <div className="loading" aria-live="polite">Loading the source analysis…</div>;

 if(overview.isError)return <ErrorPanel message={overview.error.message} retry={()=>void overview.refetch()}/>;

 const data=overview.data,sources=data.sources;

 const totalRows=sources.reduce((n,s)=>n+s.rows,0),missing=sources.reduce((n,s)=>n+s.missing_cells,0),duplicates=sources.reduce((n,s)=>n+s.duplicate_excess,0);

 const categories=[...new Set(sources.flatMap(s=>Object.keys(s.issue_counts)))].sort();

 const visible=sources.filter(s=>s.name.includes(search.toLowerCase())&&(!role||s.role===role)&&(!category||category in s.issue_counts)).sort((a,b)=>sort==='rows'?b.rows-a.rows:sort==='missing'?(b.missing_percent??-1)-(a.missing_percent??-1):a.name.localeCompare(b.name));

 const view=detail.data?.profile,numeric=view?.columns.filter(c=>c.expected_type==='number'||c.expected_type==='binary')??[],distribution=numeric.find(c=>c.name===metric)??numeric[0];

 const measurement=distribution?.distributions.find(d=>d.label===unit)??distribution?.distributions[0]??distribution;
 const dates=sources.filter(s=>s.date_coverage).flatMap(s=>[Date.parse(s.date_coverage!.minimum),Date.parse(s.date_coverage!.maximum)]),lo=Math.min(...dates,Date.parse(data.baseline.start)),hi=Math.max(...dates,Date.parse(data.baseline.end));

 const pos=(d:string)=>100*(Date.parse(d)-lo)/(hi-lo||1);

 return <>

 <section className="analysis-intro"><div><p className="eyebrow">PHASE 02 / KNOW YOUR SOURCES</p><h1>Evidence before decisions.</h1><p className="lead">Explore the exports, understand their limits, and see how the pieces connect.</p></div><span className="phase-badge"><span className="status-dot"/> {sources.length} sources profiled</span></section>

 <div className="analysis-toolbar"><div className="segmented" aria-label="Analysis period">{(['full','baseline'] as const).map(s=><button key={s} aria-pressed={scope===s} onClick={()=>{setScope(s);setOffset(0);setMetric('');}}>{s==='full'?'Full exports':'Baseline period'}</button>)}</div><p>{scope==='full'?'All exported records':'01 Sep 2025 – 31 Aug 2026'} <span className="muted">· raw records retained</span></p></div>

 <section className="stats" aria-label="Analysis summary">{[{value:fmt(totalRows),title:'Records inspected',note:scope==='baseline'?'Includes overlapping weeks and snapshot context':'Across the 13 core exports'},{value:fmt(missing),title:'Missing data cells',note:'Excludes expected optional / non-applicable blanks'},{value:fmt(duplicates),title:'Duplicate candidates',note:'Excess identical rows · none removed'},{value:`${sources.filter(s=>Object.keys(s.issue_counts).length).length} / 13`,title:'Sources with findings',note:'Warnings are visible, not silently resolved'}].map(s=><article key={s.title}><p>{s.title}</p><strong>{s.value}</strong><small>{s.note}</small></article>)}</section>

 <div className="notice"><span aria-hidden="true">ⓘ</span><p>This is exploratory analysis. Missing values are unknown. Monitoring is separate from billed costs; CHF, energy, carbon and savings calculations come in later phases.</p></div>

 <section className="chart-grid" aria-label="Data quality visualizations">

 <article className="panel"><div className="panel-heading"><div><p className="eyebrow">COMPLETENESS</p><h2>Where information is missing</h2></div><span className="chart-unit">% of all cells</span></div><p className="chart-note">Unrecorded applicable fields / (rows × columns). Optional text and non-applicable metrics excluded from the numerator.</p><Plot><Chart data={sources.map(s=>({name:short(s.name),value:s.missing_percent??0}))} percent/></Plot></article>

 <article className="panel"><div className="panel-heading"><div><p className="eyebrow">REPEATED RECORDS</p><h2>Duplicates to investigate</h2></div><span className="chart-unit">excess rows</span></div><p className="chart-note">Exact raw-field matches. Repeated business keys are reported separately in source details.</p><Plot><Chart data={sources.map(s=>({name:short(s.name),value:s.duplicate_excess}))} color="#bc8850"/></Plot></article>

 <article className="panel coverage-panel"><div className="panel-heading"><div><p className="eyebrow">TIME COVERAGE</p><h2>Exports against the baseline</h2></div><span className="legend"><i/> official baseline</span></div><p className="chart-note">Min/max event dates show the extent of observations, not continuous coverage. Inspect gaps below.</p><div className="coverage-axis"><span>{new Date(lo).toISOString().slice(0,10)}</span><span>{new Date(hi).toISOString().slice(0,10)}</span></div>{sources.map(s=><div className="coverage-row" key={s.name}><span>{short(s.name)}</span>{s.date_coverage?<div className="coverage-track" aria-label={`${s.name}: ${s.date_coverage.minimum} to ${s.date_coverage.maximum}`}><div className="baseline-band" style={{left:`${pos(data.baseline.start)}%`,width:`${pos(data.baseline.end)-pos(data.baseline.start)}%`}}/><div className="coverage-bar" title={`${s.date_coverage.minimum} → ${s.date_coverage.maximum}`} style={{left:`${pos(s.date_coverage.minimum)}%`,width:`${Math.max(.5,pos(s.date_coverage.maximum)-pos(s.date_coverage.minimum))}%`}}/></div>:<span className="muted">Snapshot / master context</span>}</div>)}</article>

 <article className="panel"><p className="eyebrow">QUALITY SIGNALS</p><h2>What needs attention</h2><p className="chart-note">Findings and groups by category. Counts overlap and are not distinct bad rows.</p><Plot><Chart data={categories.map(c=>({name:human(c),value:sources.reduce((n,s)=>n+(s.issue_counts[c]??0),0)})).sort((a,b)=>b.value-a.value).slice(0,8)} color="#687e99"/></Plot></article>

 </section>

 <section id="catalog" className="panel catalog"><div className="panel-heading"><div><p className="eyebrow">THE SOURCE CATALOG</p><h2>13 exports. Different kinds of evidence.</h2></div><span className="muted">Select a source to explore ↓</span></div><div className="filters"><label>Find source<input aria-label="Find source" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search file names…"/></label><label>Evidence type<select aria-label="Evidence type" value={role} onChange={e=>setRole(e.target.value)}><option value="">All types</option>{[...new Set(sources.map(s=>s.role))].map(r=><option key={r}>{r}</option>)}</select></label><label>Issue category<select aria-label="Issue category" value={category} onChange={e=>setCategory(e.target.value)}><option value="">All issues</option>{categories.map(c=><option key={c} value={c}>{human(c)}</option>)}</select></label><label>Sort by<select aria-label="Sort by" value={sort} onChange={e=>setSort(e.target.value)}><option value="name">Source name</option><option value="rows">Most records</option><option value="missing">Most missing data</option></select></label></div>

 <Table><thead><tr><th>Source</th><th>Evidence type</th><th>Rows</th><th>Fields</th><th>Missing cells</th><th>Duplicate excess</th><th>Gap periods</th></tr></thead><tbody>{visible.map(s=><tr key={s.name} className={selected===s.name?'selected-row':''}><td><button className="source-link" aria-pressed={selected===s.name} onClick={()=>selectSource(s.name)}>{s.name}<span>{s.cadence}</span></button></td><td><span className="type-tag">{s.role}</span></td><td>{fmt(s.rows)}</td><td>{s.column_count}</td><td>{s.missing_percent===null?'N/A':`${s.missing_percent.toFixed(1)}%`}</td><td>{s.duplicate_excess||'—'}</td><td>{s.date_coverage&&['daily','weekly','monthly'].includes(s.cadence)?s.gap_count:'N/A'}</td></tr>)}</tbody></Table>{!visible.length&&<p className="empty">No sources match these filters. Clear the search or choose another category.</p>}</section>

 <section id="explorer" className="panel explorer" aria-label="Source explorer"><div className="panel-heading"><div><p className="eyebrow">SOURCE EXPLORER</p><h2>{selected}</h2></div><span className="type-tag">{detail.data?.role??'Loading…'}</span></div><div className="tabs" aria-label="Source detail views">{[['columns','Fields & distributions'],['issues','Issues & evidence'],['joins','Coverage & joins'],['mapping','Canonical map']].map(([key,title])=><button key={key} aria-pressed={tab===key} onClick={()=>setTab(key)}>{title}</button>)}</div>

 {detail.isPending?<p className="loading">Loading source details…</p>:detail.isError?<ErrorPanel message={detail.error.message} retry={()=>void detail.refetch()}/>:view&&<><p className="scope-note">{view.scope_note} Source references count logical CSV records; header = 1.</p>

 {tab==='columns'&&<><div className="detail-stats"><span><strong>{fmt(view.rows)}</strong> records</span><span><strong>{view.column_count}</strong> fields</span><span><strong>{view.blank_cells-view.missing_cells}</strong> expected blanks</span><span><strong>{view.unique_key_count}</strong> distinct candidate keys</span></div><p className="chart-note">Candidate key: <code>{view.candidate_key.join(' + ')}</code>. A proposed grain, not an authoritative primary key.</p>

 <Table><thead><tr><th>Field</th><th>Expected / observed</th><th>Completeness</th><th>Missing</th><th>Expected blanks</th><th>Invalid</th><th>Observed range</th></tr></thead><tbody>{view.columns.map(c=><tr key={c.name}><td><code>{c.name}</code></td><td>{c.expected_type} / {c.observed_type}</td><td><div className="mini-meter" title={`${view.rows-c.blanks} nonblank of ${view.rows} rows`}><i style={{width:`${view.rows?100*(view.rows-c.blanks)/view.rows:0}%`}}/></div></td><td>{c.missing}</td><td>{c.expected_blank}</td><td>{c.invalid}</td><td>{c.minimum??'—'} → {c.maximum??'—'}</td></tr>)}</tbody></Table>

 {numeric.length>0&&<div className="distribution"><div className="panel-heading"><div><h3>Measurement distribution</h3><p className="chart-note">Raw numeric observations, separated by unit/currency where applicable. Blanks and invalid values excluded; duplicate candidates retained.</p></div><label>Measurement<select aria-label="Measurement" value={distribution?.name??''} onChange={e=>{setMetric(e.target.value);setUnit('');}}>{numeric.map(c=><option key={c.name}>{c.name}</option>)}</select></label>{!!distribution?.distributions.length&&<label>Unit / currency<select aria-label="Unit / currency" value={distribution.distributions.find(d=>d.label===unit)?.label??distribution.distributions[0].label} onChange={e=>setUnit(e.target.value)}>{distribution.distributions.map(d=><option key={d.label}>{d.label}</option>)}</select></label>}</div>{measurement&&<><div className="detail-stats"><span>Min <strong>{measurement.minimum??'N/A'}</strong></span><span>Median <strong>{measurement.median?.toFixed(2)??'N/A'}</strong></span><span>Mean <strong>{measurement.mean?.toFixed(2)??'N/A'}</strong></span><span>Max <strong>{measurement.maximum??'N/A'}</strong></span></div><Plot><Chart horizontal={false} data={measurement.histogram.map(b=>({name:b.label,value:b.count}))}/></Plot></>}</div>}

 {Object.keys(view.categories).length>0&&<><h3>Units, currencies and record status</h3><div className="category-grid">{Object.entries(view.categories).map(([col,values])=><article className="subpanel" key={col}><h4>{col}</h4>{Object.entries(values).map(([value,count])=><div className="category-row" key={value}><span>{value||'(blank)'}</span><strong>{fmt(count)}</strong></div>)}</article>)}</div></>}

 {view.amounts.length>0&&<><h3>Credits and amounts</h3><p className="chart-note">Counts by original currency and charge/status; no FX conversion or spend reconciliation.</p><Table><thead><tr><th>Currency</th><th>Charge / status</th><th>Rows</th><th>Missing amounts</th><th>Negative amounts</th></tr></thead><tbody>{view.amounts.map((a,i)=><tr key={i}><td>{a.currency}</td><td>{a.charge_type}</td><td>{a.rows}</td><td>{a.missing}</td><td>{a.negative_count}</td></tr>)}</tbody></Table></>}

 </>}

 {tab==='issues'&&<><div className="detail-stats"><span><strong>{view.duplicate_excess}</strong> exact duplicate excess</span><span><strong>{view.key_collision_groups.length}</strong> key collision groups</span><span><strong>{view.contract_conflicts.length}</strong> Draft / Final coexistence groups</span></div><label>Filter findings<select aria-label="Filter findings" value={issueCode} onChange={e=>{setIssueCode(e.target.value);setOffset(0);}}><option value="">All findings</option>{Object.entries(view.issue_counts).map(([c,n])=><option key={c} value={c}>{human(c)} ({n})</option>)}</select></label>

 {issues.isPending?<p>Loading findings…</p>:issues.isError?<ErrorPanel message={issues.error.message} retry={()=>void issues.refetch()}/>:issues.data&&<><p className="chart-note">{issues.data.total} findings. Expand a finding for evidence. Several findings may refer to the same row.</p>{issues.data.items.map((i,n)=><details className="issue" key={`${offset}-${n}`}><summary><span className="issue-pill">{human(i.code)}</span><span>{i.columns.join(', ')||'Record group'}</span><strong>{fmt(i.count)} rows</strong></summary><p>{i.message}</p><p>Source: <code>{i.source}</code></p><details><summary>All logical row references ({i.rows.length})</summary><p className="row-refs">{i.rows.join(', ')}</p></details>{i.examples.map(e=><div key={e.source_row} className="evidence"><strong>Record {e.source_row}</strong>{Object.entries(e.values).map(([k,v])=><p key={k}><code>{k}</code>: {v||'(blank)'}</p>)}</div>)}</details>)}{!issues.data.total&&<p className="empty">No findings in this category.</p>}<div className="pagination"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-10))}>Previous</button><span>{issues.data.total?`${offset+1}–${Math.min(offset+10,issues.data.total)} of ${issues.data.total}`:'0 findings'}</span><button disabled={offset+10>=issues.data.total} onClick={()=>setOffset(offset+10)}>Next</button></div></>}

 {view.azure_tags&&<div className="subpanel"><h3>Azure JSON tags</h3><p>{view.azure_tags.empty_objects} empty objects · {view.azure_tags.invalid_rows.length} invalid objects</p><p>Absent keys: {Object.entries(view.azure_tags.absent_keys).map(([k,n])=>`${k}: ${n}`).join(' · ')||'none'}</p><p>Blank values: {Object.entries(view.azure_tags.blank_values).map(([k,n])=>`${k}: ${n}`).join(' · ')||'none'}</p></div>}

 {view.project_variants.length>0&&<><h3>Project identifier spellings</h3><p className="chart-note">Proposed equivalences only; unknown and raw spellings are retained.</p><Table><thead><tr><th>Source field</th><th>Proposed ID</th><th>Raw spellings and counts</th></tr></thead><tbody>{view.project_variants.map((p,i)=><tr key={i}><td>{p.column}</td><td>{p.proposed}</td><td>{Object.entries(p.variants).map(([v,n])=>`${v||'(blank)'}: ${n}`).join(' · ')}</td></tr>)}</tbody></Table></>}

 </>}

 {tab==='joins'&&<><h3>Records over time</h3>{view.monthly_rows.length?<Plot><Chart horizontal={false} data={view.monthly_rows.map(m=>({name:m.month,value:m.rows}))}/></Plot>:<p>Not applicable: snapshot or master context.</p>}<p className="chart-note">{view.boundary_rows.length} weekly records cross a baseline boundary. No proration.</p><h3>Missing observation periods</h3>{view.gaps.length?view.gaps.map((g,i)=><details key={i} className="issue"><summary>{g.entity} · {g.internal_gaps.length} internal gaps · {g.baseline_absent_periods.length} baseline absences</summary><p>{g.certainty}. Missing observations are not proof of downtime.</p><p>Internal: {g.internal_gaps.join(', ')||'None'}</p><p>Absent in baseline: {g.baseline_absent_periods.join(', ')||'None'}</p></details>):<p>No gaps within the tested cadence. Event logs do not imply continuous activity.</p>}<h3>Proposed joins</h3>{view.joins.map((j,i)=><article className="subpanel" key={i}><h4>{j.label} → {j.target}</h4><p>{j.cardinality} · {j.matched} matched · {j.unmatched} unmatched · {j.blank_keys} blank · {j.ambiguous} ambiguous · {j.ownership_conflict_rows.length} ownership conflicts · {j.missing_department_rows.length} missing departments</p><p className="chart-note">{j.notes}</p><details><summary>Unresolved row references</summary><p>Unmatched: {j.unmatched_rows.join(', ')||'None'}</p><p>Blank: {j.blank_rows.join(', ')||'None'}</p><p>Ambiguous: {j.ambiguous_rows.join(', ')||'None'}</p><p>Ownership conflict: {j.ownership_conflict_rows.join(', ')||'None'}</p><p>Missing departments: {j.missing_department_rows.join(', ')||'None'}</p></details></article>)}{!view.joins.length&&<p>This is reference or operational context; no entity join proposed.</p>}<div className="notice"><p>Billable pools and individual servers have different grains. Pool membership and allocation weights remain unresolved for Phase 3.</p></div></>}

 {tab==='mapping'&&<><h3>Where the future canonical fields will come from</h3><p className="chart-note">Documentation only. No cleaning, allocation, FX conversion or normalized table is executed here.</p><Table><thead><tr><th>Canonical field</th><th>Source</th><th>Rule / fallback</th></tr></thead><tbody>{Object.entries(detail.data!.canonical_mapping).map(([k,v])=><tr key={k}><td><code>{k}</code></td><td>{v.source==='unknown'?<span className="issue-pill">unknown</span>:v.source}</td><td>{v.rule}</td></tr>)}</tbody></Table></>}

 </>}

 </section>

 <details className="panel provenance"><summary>Provenance & analysis limits</summary><p>Report <code>{data.report_id}</code></p><p>Snapshot <code>{data.snapshot_id}</code></p><ul>{data.limitations.map(l=><li key={l}>{l}</li>)}</ul><p>Artifacts: outputs/data_quality.json and docs/DATA_MAP.md. Regenerate with <code>python -m src.profile --data data --out outputs --docs docs</code>, then restart the API.</p></details>

 </>;

}
