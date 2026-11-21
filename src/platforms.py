"""Service families shared by the dashboard's published views."""

from src.gold_baseline import key_for
from src.profile import read_csv
from src.silver_storage import silver_directory


def service_platform(family):
    return {
        "data_cluster": "Data platforms",
        "server": "Server infrastructure",
        "saas": "SaaS",
        "ai_subscription": "AI subscriptions",
        "ai_gateway": "AI gateways",
    }.get(family, "Unallocated")


def subject_platforms(gold, output):
    directory = silver_directory(output) / gold.run["silver_version"]
    assets = {row["server_id"]: row["provider"] for row in read_csv(directory / "assets.csv")[1]
              if row["record_status"] == "accepted"}
    platforms = {}
    for row in read_csv(directory / "resource_relationships.csv")[1]:
        provider = assets.get(row["server_id"])
        if provider and row["confidence"] == "high":
            subject = "resource:" + key_for(provider, row["resource_id"], "resource")
            platforms[subject] = service_platform("server")
    for row in gold.select("""
        SELECT DISTINCT subject_id FROM gold.impact_monthly
        WHERE run_id=? AND boundary_id LIKE 'platform:%'
    """):
        platforms[row["subject_id"]] = service_platform("data_cluster")
    return platforms


def subject_platform(subject, platforms):
    return platforms.get(subject, service_platform(subject.partition(":")[0]))
