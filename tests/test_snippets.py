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


def test_update_existing_gtag_does_not_replace_unrelated_ga_ids():
    html = (
        "<html><head>"
        '<script async src="https://www.googletagmanager.com/gtag/js?id=G-OLD1234"></script>'
        "<script>gtag('config', 'G-OLD1234');</script>"
        "</head><body><!-- docs mention G-KEEP9999 --></body></html>"
    )
    out, action = inject_gtag_into_html(html, "G-NEW5678")
    assert action == "updated_existing_gtag"
    assert "G-NEW5678" in out
    assert "G-OLD1234" not in out
    assert "G-KEEP9999" in out
