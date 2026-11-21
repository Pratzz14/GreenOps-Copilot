# Feasibility

## Measures at a glance

The proposal takes **15 person-days (CHF 16,500)**. It estimates **CHF 50,083
in savings in the first 12 months**, rising to **CHF 58,606 per full year**
once the changes are in place. The first-year estimate includes time to test
changes and wait for renewals.

| Decision | First 12 months | Per full year | Before acting |
| --- | ---: | ---: | --- |
| Pause the development platform during idle hours | CHF 16,261 | CHF 17,717 | Platform owner verifies job schedules and startup. Quarterly training stays online. |
| Reduce portal test capacity after go-live | CHF 11,999 | CHF 13,687 | Test platform owner confirms go-live, load-test results and separate disaster recovery capacity. |
| Renew Microsoft Copilot with 38 fewer seats | CHF 5,615 | CHF 7,734 | Procurement and product owner confirm demand and the planned 29 Jan 2027 notice deadline. |
| Pilot a smaller production setup on quiet days | CHF 6,083 | CHF 6,939 | Data Platform and Finance approve the pilot and keep month-end close protected. |
| Renew E-signature with 12 fewer seats in cost centre 4100 | CHF 2,890 | CHF 3,600 | Confirm seat demand and the planned 2 Dec 2026 notice deadline. |
| Renew Claude Team with 5 fewer seats and move the rest to annual billing | CHF 2,323 | CHF 2,617 | Approve the annual quote and prepayment, and confirm the planned 1 Dec 2026 notice deadline. |
| Renew project scheduling with 13 fewer seats in cost centre 4000 | CHF 1,759 | CHF 2,191 | Confirm seat demand and the planned 2 Dec 2026 notice deadline. |
| Renew E-signature with 7 fewer seats in cost centre 4200 | CHF 1,686 | CHF 2,100 | Confirm seat demand and the planned 2 Dec 2026 notice deadline. |
| Renew video conferencing with 15 fewer seats in cost centre 4000 | CHF 1,468 | CHF 2,022 | Confirm seat demand and the planned 29 Jan 2027 notice deadline. |

Amounts are rounded per row. The [measures CSV](../submission/template_measures_package.csv)
includes exact savings, modeled start dates, implementation effort, and the
calculation and evidence behind each action.

## Challenge targets

The submission uses the September 2025 through August 2026 Gold baseline,
including comparable-price estimates for eligible missing charges. Location-based
operating emissions include the Swiss consumption CO₂e proxy and the EEA mixed-EU
AI generation proxy. Unsupported activity remains a coverage gap.

The submitted nine-measure portfolio uses the mid assumptions and annual
savings at steady state. Energy savings total 23,849 kWh per year.

| Metric | Modeled result | Challenge requirement | Difference |
| --- | ---: | ---: | ---: |
| Annual net cost savings | CHF 58,606 (12.49%) | CHF 117,303 (25%) | CHF 58,698 short |
| Annual location-based emissions savings | 5,913 kg CO₂e (32.62%) | 7,251 kg CO₂e (40%) | 1,338 kg CO₂e short |
| Implementation cost | CHF 16,500 (15 person-days) | At most CHF 16,500 | CHF 0 remaining |

The annual cost target is 25% of CHF 469,213.99, and the emissions target is
40% of 18,126.97 kg CO₂e. Figures in the table are rounded from the unrounded
scorecard. Coverage gaps and owner approvals keep the proposal provisional.
Use the **First 12 months** view to see how renewal dates and implementation
lead times change realized savings.

Run `python -m src.exports` to export the selected portfolio and its baseline.
