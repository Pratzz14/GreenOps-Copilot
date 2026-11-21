# Limitations

- The app runs locally against the supplied synthetic case. Bronze and Silver
  expose source lineage and Silver reconciles recorded CHF. Gold uses
  a reproducible, file-backed DuckDB run with a read-only UI and API.
- The current recorded-cost subtotal excludes unknown charges and reports
  dated review records. Energy and location-based CO₂e are partial modeled subtotals. The Swiss
  factor includes imports and uses operating emissions. Mixed EU AI hosting
  uses a grid-average proxy. SaaS electricity and unsupported units remain gaps.
- Daily or weekly observations establish workload evidence at their recorded
  grain. They cannot establish an hourly safe shutdown window. The GPU
  billing-to-instance link and test-pool allocation still need confirmation.
  Date rules run in Zurich time. Future Finance closures outside the supplied
  calendar require review.
- The sample measures are blocked or subject to human review. The app publishes
  separate conditional estimates and credits only eligible measures in
  the automatic package. The submitted measures CSV contains the provisional
  portfolio used to assess the two challenge targets.
- A production deployment would replace manual source drops with managed
  ingestion, validate inventory and contract entitlements with owners, govern
  factor updates, and record approvals in an authenticated audit trail. Validate
  a proposed action in staging before any operational change.
- The extra sources add evidence and coverage, including scheduled CI jobs and
  production protection windows. Microsoft 365 storage has no service-level energy
  factor and stays a listed gap. Power BI capacity is billed as a fixed
  capacity-day, so refresh minutes establish no electricity use or saving.
- Three comparisons remain unexplained. Billed CI runner-minutes are about
  twice the logged run time. AI invoices exceed gateway tokens by 3–10%, and
  agent logs cannot establish which runs are already represented in gateway
  totals. The closest provider report comparison is cloud plus hoster, with
  a gap of about 4%.
- The supplemental review measures state activity quantities only. They carry
  no CHF, kWh or CO₂ estimate and add nothing to either package. Shifting a
  flexible job claims no CO₂ saving without hourly regional grid data.
- The submission combines German and Irish CO₂ factors with the Swiss and
  mixed-EU operating CO₂e proxies. Its target assessment remains provisional.
