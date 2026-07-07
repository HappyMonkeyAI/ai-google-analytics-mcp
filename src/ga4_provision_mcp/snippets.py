"""gtag snippet generation and safe HTML injection helpers."""

from __future__ import annotations

import re
from typing import Literal, Tuple

GTAG_PLACEHOLDER = "<!-- GA4_MEASUREMENT_ID -->"

def render_gtag_snippet(measurement_id: str) -> str:
    """Return the standard GA4 gtag.js block for a measurement ID (G-XXXXXXXX)."""
    mid = measurement_id.strip()
    if not re.fullmatch(r"G-[A-Z0-9]+", mid):
        raise ValueError(f"Invalid measurement_id format: {mid!r} (expected G-XXXXXXXX)")
    return (
        f"<!-- Google tag (gtag.js) -->\n"
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>\n'
        f"<script>\n"
        f"  window.dataLayer = window.dataLayer || [];\n"
        f"  function gtag(){{dataLayer.push(arguments);}}\n"
        f"  gtag('js', new Date());\n"
        f"  gtag('config', '{mid}');\n"
        f"</script>\n"
    )


def inject_gtag_into_html(
    html: str,
    measurement_id: str,
    *,
    strategy: Literal["before_head_close", "after_head_open"] = "before_head_close",
) -> Tuple[str, str]:
    """
    Insert gtag into HTML. Returns (new_html, action).
    action is one of: injected, replaced_existing, appended_no_head
    """
    snippet = render_gtag_snippet(measurement_id)
    if GTAG_PLACEHOLDER in html:
        return html.replace(GTAG_PLACEHOLDER, snippet.strip()), "replaced_placeholder"

    existing = re.search(
        r"googletagmanager\.com/gtag/js\?id=(G-[A-Z0-9]+)",
        html,
        re.IGNORECASE,
    )
    if existing:
        old_id = existing.group(1)
        if old_id.upper() == measurement_id.strip().upper():
            return html, "unchanged_same_id"
        # Replace measurement id in place (minimal diff)
        updated = re.sub(
            r"G-[A-Z0-9]+",
            measurement_id.strip(),
            html,
            count=0,
        )
        return updated, "updated_existing_gtag"

    head_close = re.search(r"</head>", html, re.IGNORECASE)
    if head_close:
        pos = head_close.start()
        new_html = html[:pos] + snippet + html[pos:]
        return new_html, "injected_before_head_close"

    head_open = re.search(r"<head[^>]*>", html, re.IGNORECASE)
    if head_open and strategy == "after_head_open":
        end = head_open.end()
        new_html = html[:end] + "\n" + snippet + html[end:]
        return new_html, "injected_after_head_open"

    return html + "\n" + snippet, "appended_no_head"