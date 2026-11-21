# Data snapshot

- Attribution: Sample data ALTYCA, sprintd Basel 2026.
- Source: https://github.com/Fa-Bee/sprintd-basel-green-ai-data
- Upstream commit: 30c476fb4932877744643c282e022b5c056f444c
- Local relocation date: 2026-11-20 (Europe/Berlin).
- Runtime inputs: `data/bronze/` for the core sources and templates, `data/extra/` for the bonus sources.
- Moved, not copied: 13 core source CSVs and two official submission templates.
- Every moved file matched its SHA-256 before and after relocation; contents are unchanged.
- The submission includes byte-for-byte copies of the 15 organizer bonus inputs in `data/extra/`.
- Original documentation, documents and upstream Git metadata remain in `sprintd-basel-green-ai-data/`.
- The upstream working tree will report the moved CSV paths as deleted; this is the intentional relocation. No upstream Git commit was created.
- Treat inputs as read-only. Generated artifacts belong in `outputs/`.

| File in data/bronze/ | Role | SHA-256 |
|---|---|---|
| ai_subscriptions.csv | Core source | e97515c02392c8aa99927fd2c36d59b7dd47106b70f7cedb48a29b3eff6f4f9f |
| ai_usage.csv | Core source | 9504ac11928543bdda384d338966fad32ad7c09b97a54e667a9f22ee60762011 |
| aws_costs.csv | Core source | 8eaf5d155cd8091ab208a1a385a4e52f166f2ad5f215362dd6ce2925129de39d |
| azure_costs.csv | Core source | f0adf53ef95b20958027820e93f3ae9e36426a86f5a22f5ccbc5481340e9318b |
| business_calendar.csv | Core source | 29cc16057e21f0a5c79237ca3c70976884be1fa3825800fac4ffdb3bd6a118de |
| data_platform_usage.csv | Core source | b2e9eba3fc6b6ae5dc6af958cbfd88efc90a7a3a762b13c37a7bb40cc13c6092 |
| exchange_rates.csv | Core source | 2a7689131f4c8ab12ee59c4f0d388e5711020729b547ae51dba78b66d764a291 |
| hoster_invoice.csv | Core source | a530e0571f45a2a51362743fe8d765a3343d342b62436f88ff8b0b8e498642d1 |
| it_tickets.csv | Core source | cb8197c8739e091a656f03595d2da2b9f3f7e0dc39de116867ca9bc04073110e |
| mapping_departments_tools.csv | Core source | d12ba1c00fa43ff0f6e0f2128c6fc5f613ce84cca197f0fc4820566bb2e437e1 |
| saas_contracts.csv | Core source | acb5f4d7b8e347b19d68f7181e0967b718e39cabd8e7e7d00df0b22d10c0d9d4 |
| server_inventory.csv | Core source | 2c81d215df79c356c2c5ca7a4a5e8686125cae3cb871d4f97c1aaba2bdbdef2c |
| server_metrics_weekly.csv | Core source | 77f2dd2f514347138d1a06e2d4c77356ef34ffd14552d3f94d4c07361b676299 |
| template_baseline_and_assumptions.csv | Official submission template | 28b90a6cce4aa0ef8002c63708c6d4221ab87a93d4f8f4f7e42b65cfe4f25552 |
| template_measures_package.csv | Official submission template | b52c39002eb0cf800ad22d34331bef2c5a8180b41571f6680d18d7c213d2aa97 |
