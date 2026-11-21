"""Versioned Gold factors and their measurement boundaries."""

from dataclasses import dataclass
from decimal import Decimal

SCENARIOS = ("low", "mid", "high")
SPEC = "https://www.spec.org/power_ssj2008/results/res2025q1/power_ssj2008-20250310-01503.html"
GOOGLE = "https://arxiv.org/abs/2508.15734"
PUE = "https://www.datacenters.google/efficiency/"
UBA = "https://www.umweltbundesamt.de/system/files/medien/11850/publikationen/2026-03/16_2026_CC.pdf"
SEAI = "https://www.seai.ie/data-and-insights/seai-statistics/conversion-factors"
VSE = "https://www.strom.ch/system/files/media/documents/20260115-ds-teneur-en-co2-du-mix-electrique-suisse.pdf"


@dataclass(frozen=True)
class Factor:
    name: str
    unit: str
    values: tuple[str, str, str] | None
    source: str
    rationale: str
    source_date: str
    parameter: str | None = None
    location: str | None = None
    text: str | None = None

    def value(self, scenario):
        return Decimal(self.values[SCENARIOS.index(scenario)]) if self.values else None

    def row(self, key, run):
        return {
            "run_id": run, "factor_id": key, "submission_parameter": self.parameter,
            "factor_name": self.name, "location": self.location, "valid_from": None,
            "valid_to_exclusive": None, "value_low": self.value("low"),
            "value_mid": self.value("mid"), "value_high": self.value("high"),
            "value_text": self.text, "unit": self.unit, "source_reference": self.source,
            "source_date": self.source_date, "definition_and_rationale": self.rationale,
        }


FACTORS = {
    "grid_de": Factor(
        "Germany domestic electricity consumption", "kg CO2 per kWh",
        ("0.297", "0.330", "0.363"), UBA,
        "UBA 2025 provisional domestic-consumption CO2, including electricity trade balance, "
        "330 g/kWh. Use as a baseline-period proxy with a sensitivity of ±10%.",
        "2026-03-01", "grid_mix_location_based_germany", "Germany",
    ),
    "grid_ie": Factor(
        "Ireland electricity available for final consumption", "kg CO2 per kWh",
        ("0.17802", "0.1978", "0.21758"), SEAI,
        "SEAI 2025 provisional consumption factor, 197.8 g/kWh. Includes domestic losses. "
        "Emissions outside Ireland are excluded in the source. Sensitivity of ±10%.",
        "2026-11-21", "grid_mix_location_based_ireland", "Ireland",
    ),
    "grid_ch": Factor(
        "Switzerland electricity consumption, direct CO2", "kg CO2 per kWh", None, VSE,
        "A compatible direct-CO2 consumption value including imports is unresolved. "
        "The reported lifecycle CO2e is retained separately as context.",
        "2026-01-15", "grid_mix_location_based_switzerland", "Switzerland",
    ),
    "grid_ch_operating": Factor(
        "Swiss consumption electricity including imports, operating emissions",
        "kg CO2e per kWh", ("0.026", "0.049", "0.084"), VSE,
        "VSE slide 2: domestic plus imported operating emissions in 2024, provisional 2025 "
        "and 2022. Excludes upstream emissions. This proxy is reported separately from direct CO2.",
        "2026-02-25", location="Switzerland",
    ),
    "grid_ch_context": Factor(
        "Switzerland consumption including imports, lifecycle context", "kg CO2e per kWh",
        ("0.057", "0.090", "0.135"), VSE,
        "VSE consumption mix including imports and upstream emissions. The scenarios use published "
        "2024, 2025 provisional, and 2022 values. This series is excluded from the direct-CO2 totals.",
        "2026-01-15", location="Switzerland",
    ),
    "vcpu": Factor(
        "Virtual CPU allocation", "kWh per vCPU-hour", ("0.002", "0.005", "0.010"), SPEC,
        "Planning proxy for IT power, 2–10 W per allocated vCPU. The Dell server benchmark anchors "
        "the order of magnitude. Packing, server type and utilisation are unknown in the case.",
        "2025-03-26", "energy_per_vcpu_hour",
    ),
    "database_vcore": Factor(
        "Managed database allocated vCore", "IT kWh per vCore-hour",
        ("0.002", "0.005", "0.010"), SPEC,
        "Assume one allocated vCore has the same planning power range as one vCPU. "
        "The benchmark anchors the order of magnitude. Database SKU and hardware are unknown.",
        "2025-03-26",
    ),
    "build_runner": Factor(
        "Build runner active hour", "IT kWh per runner-hour",
        ("0.004", "0.020", "0.080"), SPEC,
        "Assume 2, 4 or 8 vCPUs per billed runner with 2, 5 or 10 W allocated per vCPU. "
        "Convert billed minutes to hours. Runner size and hardware are unknown.",
        "2025-03-26",
    ),
    "node": Factor(
        "Platform cluster node", "kWh per node-hour", ("0.164", "0.350", "0.650"), SPEC,
        "Benchmark-anchored IT power scenarios for an unknown node. 164 W at idle and around "
        "501 W at 40% benchmark load inform the sensitivity. Values are workload assumptions.",
        "2025-03-26", "energy_per_node_hour",
    ),
    "gpu": Factor(
        "GPU service including host allocation", "kWh per GPU-hour", ("0.15", "0.40", "0.70"),
        "https://resources.nvidia.com/en-us-gpu-resources/h100-datasheet-24306?download=1",
        "IT power sensitivity based on an unknown accelerator profile. The H100 board rating "
        "ranges from 350–400 W PCIe to 700 W SXM. The scenario values represent assumed average "
        "power including an allocated share of a host, rather than measured device power.",
        "2026-11-21", "energy_per_gpu_hour",
    ),
    "storage": Factor(
        "Persistent storage allocation", "kWh per GB-day", ("0.00000648", "0.00001944", "0.0000648"),
        "https://www.seagate.com/content/dam/seagate/migrated-assets/www-content/datasheets/pdfs/exos-x20-channel-DS2080-2111US-en_CA.pdf",
        "5.4 W × 24 h ÷ 20,000 GB ÷ 1,000 W/kW is the disk-only floor. Mid and high use 3× "
        "and 10× for replicas, utilisation and storage-server overhead before facility PUE.",
        "2021-11-01", "energy_per_gb_storage_day",
    ),
    "tokens": Factor(
        "Gateway text tokens", "facility kWh per 1,000 tokens", ("0.00012", "0.00048", "0.0024"),
        GOOGLE,
        "Illustrative conversion of the published 0.24 Wh median Gemini text prompt assuming "
        "500 input-plus-output tokens. The 0.25× and 5× endpoints reflect model and length sensitivity. "
        "The source already includes facility overhead. Cached tokens are counted only within input.",
        "2025-08-21", "energy_per_1000_tokens",
    ),
    "message": Factor(
        "AI subscription message", "facility kWh per message", ("0.00006", "0.00024", "0.0012"),
        GOOGLE,
        "Use the 0.24 Wh Gemini Apps median as a facility proxy for one text message. "
        "Scenario multipliers are assumptions for unknown providers and workloads.",
        "2025-08-21", "energy_per_subscription_message",
    ),
    "pue": Factor(
        "Power usage effectiveness", "ratio", ("1.09", "1.35", "1.54"), PUE,
        "Google 2025 fleet PUE anchors the low scenario and its cited Uptime Institute survey "
        "anchors the high scenario. Mid is a planning assumption. Applies once to IT-only activity.",
        "2026-11-21", "pue",
    ),
    "allocation": Factor(
        "Shared cost attribution", "text", None, "Silver cost facts and ownership",
        "Direct attribution where supported. Leave ambiguous departments Unallocated, and retain "
        "pooled invoices at resource grain. Do not spread unknown balances across tenants.",
        "2026-11-21", "allocation_rule_shared_costs",
        text="Direct attribution; unresolved costs remain Unallocated.",
    ),
}

GRID = {"Germany": "grid_de", "Ireland": "grid_ie", "Switzerland": "grid_ch"}
FACILITY_FACTORS = {"tokens", "message"}
