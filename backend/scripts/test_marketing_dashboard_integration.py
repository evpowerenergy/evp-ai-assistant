#!/usr/bin/env python3
"""
Integration smoke test for marketing-dashboard-summary Edge Function + AI tool wrapper.

Usage (from backend/ with venv active):
  python scripts/test_marketing_dashboard_integration.py
  python scripts/test_marketing_dashboard_integration.py --date-from 2026-03-01 --date-to 2026-03-30

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env or environment.
Does NOT commit or push anything.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.tools.marketing_tools import get_marketing_dashboard  # noqa: E402


def _bangkok_today() -> str:
    return date.today().isoformat()


def _month_start() -> str:
    today = date.today()
    return today.replace(day=1).isoformat()


async def call_edge_function_direct(date_from: str, date_to: str) -> dict:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")

    endpoint = f"{url}/functions/v1/marketing-dashboard-summary"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": "application/json",
            },
            json={"startDate": date_from, "endDate": date_to},
        )
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:500]}

    return {
        "status_code": response.status_code,
        "body": body,
    }


def _validate_dashboard_shape(data: dict) -> list[str]:
    errors: list[str] = []
    required_top = [
        "totalSales",
        "totalAdBudget",
        "facebookAds",
        "googleAds",
        "package",
        "wholesales",
        "overallRoas",
        "meta",
    ]
    for key in required_top:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    if "package" in data:
        for k in ("sales", "newLeads", "totalQtDocuments", "win", "winRateQt", "conversionRate"):
            if k not in data["package"]:
                errors.append(f"missing package.{k}")

    if "meta" in data:
        for k in ("facebookApiConnected", "googleApiConnected", "dateFrom", "dateTo"):
            if k not in data["meta"]:
                errors.append(f"missing meta.{k}")

    return errors


async def run_case(label: str, date_from: str, date_to: str) -> bool:
    print(f"\n=== {label} ({date_from} .. {date_to}) ===")

    direct = await call_edge_function_direct(date_from, date_to)
    print(f"Edge Function HTTP {direct['status_code']}")

    if direct["status_code"] == 404:
        print("FAIL: Function not deployed. Run:")
        print("  cd evp-core-platform && ./scripts/deploy-marketing-dashboard-function.sh")
        return False

    body = direct.get("body") or {}
    if not body.get("success"):
        print(f"FAIL: Edge Function error: {body.get('error', body)}")
        return False

    data = body.get("data") or {}
    shape_errors = _validate_dashboard_shape(data)
    if shape_errors:
        print("FAIL: Invalid response shape:")
        for err in shape_errors:
            print(f"  - {err}")
        return False

    print("Edge Function OK — sample metrics:")
    print(f"  totalSales: {data.get('totalSales')}")
    print(f"  totalAdBudget: {data.get('totalAdBudget')}")
    print(f"  overallRoas: {data.get('overallRoas')}")
    print(f"  package.newLeads: {data.get('package', {}).get('newLeads')}")
    print(f"  meta.facebookApiConnected: {data.get('meta', {}).get('facebookApiConnected')}")

    tool_result = await get_marketing_dashboard(
        date_from=date_from,
        date_to=date_to,
        user_id="integration-test",
        user_role="manager_marketing",
    )
    if not tool_result.get("success"):
        print(f"FAIL: AI tool wrapper error: {tool_result.get('error')}")
        return False

    if tool_result["data"].get("totalSales") != data.get("totalSales"):
        print("FAIL: Tool wrapper totalSales mismatch with Edge Function")
        return False

    print("AI tool wrapper OK — matches Edge Function totalSales")
    return True


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-from", default=_bangkok_today())
    parser.add_argument("--date-to", default=_bangkok_today())
    parser.add_argument("--all-presets", action="store_true", help="Run today, month-to-date presets")
    args = parser.parse_args()

    cases = [("custom", args.date_from, args.date_to)]
    if args.all_presets:
        today = _bangkok_today()
        cases = [
            ("today", today, today),
            ("month-to-date", _month_start(), today),
        ]

    ok = True
    for label, df, dt in cases:
        passed = await run_case(label, df, dt)
        ok = ok and passed

    print("\n" + ("ALL PASSED" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
