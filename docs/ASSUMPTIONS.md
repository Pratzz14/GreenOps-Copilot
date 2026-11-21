# Gold calculation assumptions

The baseline spans September 2025 through August 2026. The scorecard uses the
mid steady-state annual estimate for submission and reports the first 12
months following the decision separately. The first-year illustration prorates
changes by days after their indicated effective date. Independently verified
seasonal usage for the prospective year would support a more precise schedule.

- **Spend.** Each eligible Silver charge contributes once at its original
  billing grain after monthly CHF conversion. Treat spending with missing
  amounts or unresolved records as a recorded subtotal. Charges with unclear
  ownership remain Unallocated. Pooled resources retain their billed grain.
- **Compute and storage.** Development and production use observed node-hours
  as the activity stream. Other supported vCPU-hour, GPU-hour, and GB-day
  amounts come from billing. Monitoring of an unlinked asset provides evidence
  for review. Unit-specific estimates use benchmark-anchored ranges. Apply PUE
  once to IT-side energy. Capacity-days, network GB, and other
  units with no validated physical conversion remain open.
- **AI and SaaS.** Gateway input tokens already include cached input. Add
  output once. AI subscription message estimates use their separate activity
  stream. The Gemini facility energy benchmark is an illustrative text-model
  proxy with wide sensitivity. It already covers facility overhead. SaaS seats
  show utilisation where available. Operating energy stays unknown when there
  is no defensible activity proxy.
- **Grid factors.** Germany and Ireland use 2025 direct-CO₂ consumption
  references with ±10% sensitivity as a proxy for the baseline period.
  Ireland's source covers emissions within Ireland. The Swiss consumption
  reference includes imports and reports lifecycle CO₂e. It appears as a
  separately labeled factor. The direct-CO₂ field remains open.
  [Germany UBA](https://www.umweltbundesamt.de/system/files/medien/11850/publikationen/2026-03/16_2026_CC.pdf) ·
  [Ireland SEAI](https://www.seai.ie/data-and-insights/seai-statistics/conversion-factors) ·
  [Swiss VSE](https://www.strom.ch/system/files/media/documents/20260115-ds-teneur-en-co2-du-mix-electrique-suisse.pdf)
- **Measures.** Illustrative power scheduling retains quarterly training and
  uses positive, attributable variable prices only. Confirm billing effects,
  startup costs and the proposed schedule before approval. Licence estimates
  hold the workload fixed and credit no operational energy savings. August
  seat usage, indicative notice deadlines and one-time effort estimates are
  shown with their evidence. Contracted savings depend on verified renewal
  and notice terms.

The versioned registry contains all factor values, ranges, and sources.
[Factor registry](../src/factors.py)


## P0 baseline extensions

- Gold estimates missing metered charges separately from the reconciled Silver
  subtotal. An estimate uses the missing line's quantity, the median unit
  price from at least three positive same-month comparable usage lines, and
  the existing monthly exchange rate. Review and duplicate cases are excluded.
- The Swiss operating CO2e estimate uses 0.026, 0.049 and 0.084 kg CO2e/kWh
  from the domestic and import operating components in VSE slide 2.
  The scenarios represent 2024, provisional 2025 and 2022. The Dashboard
  exposes this estimate separately. The official direct-CO2 score remains
  unassessed until a compatible factor and sufficient coverage are available.
- vCore-hours use the benchmark-anchored vCPU power range as a database proxy.
  Build runner minutes are divided by 60 and multiplied by a planning range
  for a 2, 4 or 8 vCPU runner. PUE is applied once. The actual configurations
  are unknown. Network, reporting capacity and generic SaaS still have gaps.
- The optimizer evaluates all candidates and collapses interchangeable-cost,
  independent licence choices into ranked prefixes. This preserves the exact
  annual package objective, including the implementation cap.
- A SaaS reduction is eligible for modeled selection when three Final months
  establish persistent unused seats, all three months have accepted positive
  prices, and the dated notice period is still open. The model assumes renewal
  at the latest observed price and no minimum above the retained seats.
- Exact priced aggregate mirrors in Azure or AWS count once in Silver, with a
  lineage link to the missing-amount copy. Gold keeps their recovered subtotal
  inside recorded CHF. For imputed charges, evidence identifies each missing
  line, price-comparison rows, the median unit rate and the FX input.
- The Gold build attaches optional scheduler and backup records on exact
  resource references and includes their source hashes in the run identity.
  The test-pool sensitivity protects March 2026 and linked job days. It
  applies a 10–30% change to variable billed units outside those dates.
  Disaster-recovery capacity and actual billing effects need verification.
