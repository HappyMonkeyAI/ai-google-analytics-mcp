import json
from pathlib import Path

import pytest

from ga4_provision_mcp import inventory as inv


def test_scan_local_configs(tmp_path):
    proj = tmp_path / "alpha"
    proj.mkdir()
    cfg = proj / ".ga4.config.json"
    cfg.write_text(
        json.dumps(
            {
                "measurement_id": "G-SCAN1234",
                "property_id": "111",
                "website_url": "https://alpha.example",
                "stream_name": "Alpha Web",
            }
        ),
        encoding="utf-8",
    )
    out = inv.scan_local_ga4_configs([str(tmp_path)])
    assert out["count"] == 1
    assert out["configs"][0]["measurement_id"] == "G-SCAN1234"


def test_detect_nextjs_stack(tmp_path):
    web = tmp_path / "web"
    (web / "src" / "app").mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    (web / "src" / "app" / "layout.tsx").write_text("export default function L() {}", encoding="utf-8")
    stack = inv.detect_tracking_stack(tmp_path)
    assert stack["ok"] is True
    assert stack["recommended_mode"] == "nextjs"
    assert stack["suggested_web_roots"]


def test_detect_html_stack(tmp_path):
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "index.html").write_text("<html></html>", encoding="utf-8")
    stack = inv.detect_tracking_stack(tmp_path)
    assert stack["recommended_mode"] == "html"
    assert stack["html_paths"]


def test_list_projects_needing_ga4(registry_style, monkeypatch):
    reg, demo, other = registry_style
    monkeypatch.setenv("GA4_LAUNCHER_REGISTRY_JSON", str(reg))
    (demo / ".ga4.config.json").write_text(
        json.dumps({"measurement_id": "G-OK1234"}), encoding="utf-8"
    )
    out = inv.list_projects_needing_ga4(include_partial=False)
    assert out["ok"] is True
    slugs = {p["slug"] for p in out["projects"]}
    assert "needs-ga4" in slugs
    assert "has-ga4" not in slugs


@pytest.fixture
def registry_style(tmp_path):
    demo = tmp_path / "has"
    needs = tmp_path / "needs"
    demo.mkdir()
    needs.mkdir()
    data = {
        "version": "1.1.0",
        "projects": [
            {"slug": "has-ga4", "name": "Has", "path": str(demo), "url": "https://has.example"},
            {
                "slug": "needs-ga4",
                "name": "Needs",
                "path": str(needs),
                "url": "https://needs.example",
            },
        ],
    }
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps(data), encoding="utf-8")
    return reg, demo, needs