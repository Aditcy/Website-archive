from app.crawler.normalize import norm


def test_norm_removes_fragment():
    assert norm(
        "https://example.com/a#section"
    ) == "https://example.com/a"


def test_norm_removes_tracking_parameters():
    assert norm(
        "https://example.com/a?utm_source=x&x=1&fbclid=abc&gclid=xyz"
    ) == "https://example.com/a?x=1"


def test_norm_preserves_meaningful_query_parameters():
    assert norm(
        "https://example.com/search?q=test&page=2"
    ) == "https://example.com/search?q=test&page=2"


def test_norm_normalizes_hostname():
    assert norm(
        "https://EXAMPLE.COM/a"
    ) == "https://example.com/a"


def test_norm_normalizes_default_https_port():
    assert norm(
        "https://example.com:443/a"
    ) == "https://example.com/a"


def test_norm_normalizes_default_http_port():
    assert norm(
        "http://example.com:80/a"
    ) == "http://example.com/a"


def test_norm_preserves_non_default_port():
    assert norm(
        "https://example.com:8443/a"
    ) == "https://example.com:8443/a"


def test_norm_rejects_non_http_urls():
    assert norm("mailto:test@example.com") is None
    assert norm("javascript:void(0)") is None


def test_norm_adds_root_path():
    assert norm(
        "https://example.com"
    ) == "https://example.com/"
