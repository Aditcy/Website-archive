from app.crawler.sitemap import urls, get


def test_urls_extracts_sitemap_urls():
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/</loc>
        </url>
        <url>
            <loc>https://example.com/about</loc>
        </url>
    </urlset>
    """

    assert urls(xml) == [
        "https://example.com/",
        "https://example.com/about",
    ]


def test_urls_handles_namespaces():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc> https://example.com/page </loc>
        </url>
    </urlset>
    """

    assert urls(xml) == [
        "https://example.com/page",
    ]


def test_urls_handles_sitemap_index():
    xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://example.com/sitemap-1.xml</loc>
        </sitemap>
        <sitemap>
            <loc>https://example.com/sitemap-2.xml</loc>
        </sitemap>
    </sitemapindex>
    """

    assert urls(xml) == [
        "https://example.com/sitemap-1.xml",
        "https://example.com/sitemap-2.xml",
    ]


def test_urls_returns_empty_for_invalid_xml():
    assert urls("<not-valid-xml") == []


def test_urls_returns_empty_for_empty_input():
    assert urls("") == []


def test_get_returns_empty_for_http_error(monkeypatch):
    class Response:
        status_code = 404
        text = "not found"

    monkeypatch.setattr(
        "app.crawler.sitemap.httpx.get",
        lambda *args, **kwargs: Response(),
    )

    assert get(
        "https://example.com/sitemap.xml",
        {"User-Agent": "TestBot"},
    ) == ""


def test_get_returns_response_text(monkeypatch):
    class Response:
        status_code = 200
        text = "<urlset></urlset>"

    monkeypatch.setattr(
        "app.crawler.sitemap.httpx.get",
        lambda *args, **kwargs: Response(),
    )

    assert get(
        "https://example.com/sitemap.xml",
        {"User-Agent": "TestBot"},
    ) == "<urlset></urlset>"


def test_get_handles_request_exception(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("connection failed")

    monkeypatch.setattr(
        "app.crawler.sitemap.httpx.get",
        broken,
    )

    assert get(
        "https://example.com/sitemap.xml",
        {"User-Agent": "TestBot"},
    ) == ""
