import json
import os
from pathlib import Path

import pytest

from ga4_provision_mcp import integrations as ig


@pytest.fixture
def registry_file(tmp_path, monkeypatch):
    data = {
        "version": "1.1.0",
        "projects": [
            {
                "slug": "demo-app",
                "name": "Demo",
                "path": str(tmp_path / "demo"),
                "url": "https://demo.example",
            }
        ],
    }
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("GA4_LAUNCHER_REGISTRY_JSON", str(reg))
    (tmp_path / "demo").mkdir()
    return reg, tmp_path / "demo"


def test_launcher_unavailable_without_env(monkeypatch):
    monkeypatch.delenv("GA4_LAUNCHER_REGISTRY_JSON", raising=False)
    monkeypatch.delenv("LAUNCHER_REGISTRY_JSON", raising=False)
    st = ig.launcher_status()
    assert st["available"] is False


def test_list_and_resolve(registry_file):
    _, demo = registry_file
    listed = ig.list_launcher_projects()
    assert listed["ok"] is True
    assert listed["count"] == 1
    resolved = ig.resolve_project_for_ga4(slug="demo-app")
    assert resolved["ok"] is True
    assert resolved["suggested_website_url"] == "https://demo.example"
    assert resolved["project_dir"] == str(demo)


def test_read_ga4_config(registry_file):
    _, demo = registry_file
    cfg_path = demo / ".ga4.config.json"
    cfg_path.write_text(
        json.dumps({"measurement_id": "G-TEST123", "website_url": "https://demo.example"}),
        encoding="utf-8",
    )
    row = ig.get_launcher_project("demo-app")
    assert row["found"]
    assert row["project"]["ga4_config"]["found"] is True


def test_sync_requires_writable(registry_file):
    out = ig.sync_ga4_to_launcher_registry(
        "demo-app", "G-ABCD1234", "999", website_url="https://demo.example"
    )
    assert out["ok"] is False
    assert "read-only" in out["error"].lower() or "writable" in out["error"].lower()


def test_sync_writes_when_writable(registry_file, monkeypatch):
    reg, _ = registry_file
    monkeypatch.setenv("GA4_LAUNCHER_REGISTRY_WRITABLE", "true")
    out = ig.sync_ga4_to_launcher_registry(
        "demo-app", "G-ABCD1234", "999", website_url="https://demo.example"
    )
    assert out["ok"] is True
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert data["projects"][0]["analytics"]["ga4"]["measurement_id"] == "G-ABCD1234"


def test_keymaster_bootstrap_detection(registry_file):
    _, demo = registry_file
    km_dir = demo / ".keymaster"
    km_dir.mkdir()
    (km_dir / "project.key").write_text(
        json.dumps({"project_slug": "demo-app", "client_id": "x"}),
        encoding="utf-8",
    )
    km = ig.keymaster_bootstrap_at(demo)
    assert km["available"] is True
    assert km["project_slug"] == "demo-app"
    assert "client_secret" not in km