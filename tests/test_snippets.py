from ga4_provision_mcp.snippets import inject_gtag_into_html, render_gtag_snippet


def test_render_gtag_snippet():
    s = render_gtag_snippet("G-ABCD1234")
    assert "G-ABCD1234" in s
    assert "googletagmanager.com/gtag/js" in s


def test_inject_before_head_close():
    html = "<html><head><title>x</title></head><body></body></html>"
    out, action = inject_gtag_into_html(html, "G-TEST1234")
    assert action == "injected_before_head_close"
    assert "G-TEST1234" in out
    assert out.index("G-TEST1234") < out.lower().index("</head>")


def test_dry_run_unchanged_same_id():
    html = '<script src="https://www.googletagmanager.com/gtag/js?id=G-SAME1234"></script>'
    out, action = inject_gtag_into_html(html, "G-SAME1234")
    assert action == "unchanged_same_id"
    assert out == html