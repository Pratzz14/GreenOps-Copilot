"""Project monthly recurring spending for comparable recommendation scopes."""

from datetime import date
from decimal import Decimal

CENTS = Decimal("0.01")


def offset_month(month, offset):
    year, index = divmod(month.year * 12 + month.month - 1 + offset, 12)
    return date(year, index + 1, 1)


def historical_months(start, stop):
    first_complete = start if start.day == 1 else offset_month(start, 1)
    months = [offset_month(stop, offset) for offset in (-3, -2, -1)]
    return [month.isoformat()[:7] for month in months if month >= first_complete]


def forecast_scope(member, history_months, decision):
    history = [member.get("projection_history", {}).get(month) for month in history_months]
    if len(history) != 3 or any(value is None or value < 0 for value in history):
        return None
    baseline = sum(history) / len(history)
    measure = member["estimate"] or {}
    annual = next((row for row in measure.get("estimates", []) if row["horizon"] == "steady_state"), {})
    licence = member.get("licence_spend")
    if licence:
        savings, effective = licence["annual"], licence["effective_date"]
    else:
        savings, effective = annual.get("net_chf"), measure.get("earliest_effective_date")
    if effective is None or savings is None or savings <= 0 or savings > baseline * 12:
        return None
    conditional = member["safety_status"] != "eligible" or (not licence and annual.get("estimate_status") == "conditional")
    return history, baseline, savings / 12, max(decision, effective), conditional


def spending_projection(members, total_scopes, history_months, forecast_start, decision):
    scopes = [scope for member in members if (scope := forecast_scope(member, history_months, decision)) is not None]
    if not scopes:
        return None
    history = [{"month": month, "published_chf": sum(scope[0][index] for scope in scopes).quantize(CENTS)}
               for index, month in enumerate(history_months)]
    baseline = sum(scope[1] for scope in scopes)
    points = []
    for offset in range(12):
        month, end = offset_month(forecast_start, offset), offset_month(forecast_start, offset + 1)
        days = Decimal((end - month).days)
        avoided = sum(rate * max(0, (end - max(month, effective)).days) / days
                      for _, _, rate, effective, _ in scopes)
        points.append({"month": month.isoformat()[:7], "current_chf": baseline.quantize(CENTS),
                       "if_followed_chf": (baseline - avoided).quantize(CENTS)})
    return {"history": history, "forecast": points,
            "savings_chf": sum(point["current_chf"] - point["if_followed_chf"] for point in points),
            "effective_dates": sorted({scope[3] for scope in scopes}),
            "covered_scopes": len(scopes), "total_scopes": total_scopes,
            "conditional": any(scope[4] for scope in scopes)}
