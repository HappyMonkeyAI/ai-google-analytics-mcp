import pytest

from ga4_provision_mcp.nextjs import (
    inject_google_analytics_into_layout,
    render_nextjs_env_line,
    render_nextjs_ga4_component,
    scaffold_nextjs_ga4,
    upsert_env_measurement_id,
)


def test_render_nextjs_component_env_mode():
    src = render_nextjs_ga4_component("G-ABCD1234", mode="env")
    assert "NEXT_PUBLIC_GA_MEASUREMENT_ID" in src
    assert "next/script" in src


def test_render_nextjs_env_line():
    assert render_nextjs_env_line("G-TEST9999") == "NEXT_PUBLIC_GA_MEASUREMENT_ID=G-TEST9999\n"


def test_inject_layout_adds_import_and_usage():
    layout = (
        'import type { Metadata } from "next";\n\n'
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return (\n"
        '    <html lang="en">\n'
        "      <body>{children}</body>\n"
        "    </html>\n"
        "  );\n"
        "}\n"
    )
    out, action = inject_google_analytics_into_layout(layout)
    assert "GoogleAnalytics" in out
    assert "<GoogleAnalytics />" in out
    assert "added_import" in action


def test_upsert_env_updates_existing():
    old = "FOO=1\nNEXT_PUBLIC_GA_MEASUREMENT_ID=G-OLD1234\n"
    new, action = upsert_env_measurement_id(old, "G-NEW5678")
    assert action == "updated_env_var"
    assert "G-NEW5678" in new
    assert "G-OLD1234" not in new


def test_scaffold_nextjs_dry_run(tmp_path):
    web = tmp_path / "web"
    (web / "src" / "app").mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    layout = (
        'import type { Metadata } from "next";\n\n'
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return (\n"
        '    <html lang="en">\n'
        "      <body>{children}</body>\n"
        "    </html>\n"
        "  );\n"
        "}\n"
    )
    (web / "src" / "app" / "layout.tsx").write_text(layout, encoding="utf-8")

    result = scaffold_nextjs_ga4(str(web), "G-SCAFFOLD1", dry_run=True)
    assert result["layout_action"] == "added_import+injected_after_body"
    assert result["dry_run"] is True
    assert not (web / "src" / "components" / "GoogleAnalytics.tsx").exists()


def test_scaffold_nextjs_root_app_layout_uses_valid_relative_import(tmp_path):
    web = tmp_path / "web"
    (web / "app").mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    (web / "app" / "layout.tsx").write_text(
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return <html><body>{children}</body></html>;\n"
        "}\n",
        encoding="utf-8",
    )

    result = scaffold_nextjs_ga4(str(web), "G-SCAFFOLD1", layout_relative="app/layout.tsx")

    layout = (web / "app" / "layout.tsx").read_text(encoding="utf-8")
    assert result["import_path"] == "../components/GoogleAnalytics"
    assert 'from "../components/GoogleAnalytics"' in layout


def test_inject_layout_ignores_google_analytics_comment_when_adding_import():
    layout = (
        "// GoogleAnalytics is not wired yet\n"
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return <html><body>{children}</body></html>;\n"
        "}\n"
    )
    out, action = inject_google_analytics_into_layout(layout)
    assert 'import { GoogleAnalytics } from "@/components/GoogleAnalytics";' in out
    assert "<GoogleAnalytics />" in out
    assert action == "prepended_import+injected_after_body"
