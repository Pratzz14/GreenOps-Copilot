# Limitations

- The app runs locally against the supplied synthetic case. Bronze and Silver
  expose source lineage and Silver reconciles recorded CHF. Gold uses
  a reproducible, file-backed DuckDB run with a read-only UI and API.
- The current recorded-cost subtotal excludes unknown charges and reports
  dated review records. Energy and direct-CO₂ are partial modeled subtotals.
  The Swiss lifecycle CO₂e factor is context for the location mix. Mixed AI
  and SaaS locations and unsupported activity units remain coverage gaps.
- Daily or weekly observations establish workload evidence at their recorded
  grain. They cannot establish an hourly safe shutdown window. The GPU
  billing-to-instance link and test-pool allocation still need confirmation.
  Date rules run in Zurich time. Future Finance closures outside the supplied
  calendar require review.
- The sample measures are blocked or subject to human review. The app publishes
  separate conditional estimates and credits only eligible measures in
  the automatic package. The case submission files are drafts.
- A production deployment would replace manual source drops with managed
  ingestion, validate inventory and contract entitlements with owners, govern
  factor updates, and record approvals in an authenticated audit trail. Validate
  a proposed action in staging before any operational change.
