"""Google Analytics Admin API helpers (provisioning + light discovery)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.analytics.admin_v1beta.types import DataStream, Property


class AdminApiError(RuntimeError):
    """Raised when the Admin API call fails or credentials are missing."""


def _client() -> AnalyticsAdminServiceClient:
    try:
        return AnalyticsAdminServiceClient()
    except Exception as exc:  # pragma: no cover - env specific
        raise AdminApiError(
            "Could not create AnalyticsAdminServiceClient. "
            "Run gcloud application-default login with analytics.edit scope. "
            f"Detail: {exc}"
        ) from exc


def normalize_account_id(account_id: str) -> str:
    digits = re.sub(r"\D", "", account_id or "")
    if not digits:
        raise ValueError("account_id must contain numeric GA account id")
    return digits


def normalize_property_id(property_id: str) -> str:
    raw = (property_id or "").strip()
    if raw.startswith("properties/"):
        raw = raw.split("/", 1)[1]
    if not raw.isdigit():
        raise ValueError("property_id must be numeric or properties/<id>")
    return raw


def default_account_id() -> Optional[str]:
    env = os.environ.get("GA4_DEFAULT_ACCOUNT_ID", "").strip()
    return normalize_account_id(env) if env else None


def provision_property(
    account_id: str,
    project_name: str,
    *,
    timezone: str = "Europe/London",
    currency_code: str = "GBP",
    environment: str = "Production",
) -> Dict[str, Any]:
    """Create a GA4 property under the given account."""
    acct = normalize_account_id(account_id)
    display = f"{project_name.strip()} - {environment.strip()}"
    prop = Property(
        display_name=display,
        parent=f"accounts/{acct}",
        time_zone=timezone,
        currency_code=currency_code,
    )
    try:
        response = _client().create_property(property=prop)
    except Exception as exc:
        raise AdminApiError(f"create_property failed: {exc}") from exc
    prop_id = normalize_property_id(response.name)
    return {
        "property_name": response.name,
        "property_id": prop_id,
        "display_name": response.display_name,
        "parent_account": acct,
    }


def create_web_stream(
    property_id: str,
    stream_name: str,
    website_url: str,
) -> Dict[str, Any]:
    """Create a web data stream; returns measurement_id for gtag."""
    pid = normalize_property_id(property_id)
    stream = DataStream(
        type_=DataStream.DataStreamType.WEB_DATA_STREAM,
        display_name=stream_name.strip(),
        web_stream_data=DataStream.WebStreamData(default_uri=website_url.strip()),
    )
    try:
        response = _client().create_data_stream(
            parent=f"properties/{pid}",
            data_stream=stream,
        )
    except Exception as exc:
        raise AdminApiError(f"create_data_stream failed: {exc}") from exc
    measurement_id = ""
    if response.web_stream_data and response.web_stream_data.measurement_id:
        measurement_id = response.web_stream_data.measurement_id
    return {
        "data_stream_name": response.name,
        "property_id": pid,
        "display_name": response.display_name,
        "measurement_id": measurement_id,
        "default_uri": website_url.strip(),
    }


def list_account_summaries(limit: int = 20) -> List[Dict[str, Any]]:
    """Read-only discovery: account summaries (requires analytics.readonly ADC)."""
    out: List[Dict[str, Any]] = []
    try:
        client = _client()
        for i, summary in enumerate(client.list_account_summaries()):
            if i >= limit:
                break
            out.append(
                {
                    "account": summary.account,
                    "display_name": summary.display_name,
                    "property_summaries": [
                        {
                            "property": p.property,
                            "display_name": p.display_name,
                        }
                        for p in summary.property_summaries
                    ],
                }
            )
    except Exception as exc:
        raise AdminApiError(f"list_account_summaries failed: {exc}") from exc
    return out