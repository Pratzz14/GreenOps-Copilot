# Bronze exploration demo

1. Run `python -m src.profile --data data --out outputs --docs docs` in the installed Python environment.
2. Run `npm --prefix frontend run build`, then start the combined server with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001`.
3. Open [GreenOps Copilot](http://127.0.0.1:8001). Bronze opens first with the 13 original exports, what each file contains, and full-export record counts.
4. Under **Exploration completed**, compare **Full exports** with **Baseline period**. The summary and drill-downs follow the selected period. The source catalog always shows full-export counts.
5. Expand **Completeness**, **Duplicate candidates**, **Date coverage**, or **Quality findings** to see the corresponding charts.
6. Expand **Source analysis**, select `data_platform_usage.csv` under **Source**, then choose **Coverage and proposed joins** under **Analysis**. Expand `dp-dev` to inspect six missing baseline dates. Missing observations do not establish downtime. **Filter and compare source profiles** offers source search, filters and sorting.
7. Choose **Issues and evidence**, filter to exact duplicate candidates, and expand a finding to see examples and logical row references.
8. Choose **Fields and distributions** and select `active_use_h`. For an example with units and currencies, select `azure_costs.csv` and compare its quantity and cost distributions.
9. Select `ai_subscriptions.csv` to inspect Draft/Final frequencies and coexistence groups. Choose **Canonical mapping** to see proposed source fields, rules and fallbacks.
10. Expand **Provenance & analysis limits** to see the selected report and snapshot identities. Switch to **Silver** and **Gold** to see each layer’s purpose and status, then return to **Bronze** to resume your exploration.

The installed application runs offline without external assets or services.
Refresh sources via CLI and restart the API to load a new report. Run
`npm --prefix frontend run test:eda` for the desktop and mobile regression.
The test uses port 8001 by default. Set `EDA_URL` to target a different server.
