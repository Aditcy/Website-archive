from app.crawler.robots import maps, allowed


def test_maps_finds_sitemap_urls():
    txt = """
    User-agent: *
    Disallow: /private/

    Sitemap: https://example.com/sitemap.xml
    Sitemap: https://example.com/sitemap-posts.xml
    """

    assert maps(txt) == [
        "https://example.com/sitemap.xml",
        "https://example.com/sitemap-posts.xml",
    ]


def test_maps_ignores_blank_lines():
    txt = """
    Sitemap: https://example.com/sitemap.xml


    User-agent: *
    """

    assert maps(txt) == [
        "https://example.com/sitemap.xml",
    ]


def test_allowed_respects_disallow():
    class FakeRobots:
        def can_fetch(self, user_agent, url):
            return not url.endswith("/private")

    robots = FakeRobots()

    assert allowed(
        robots,
        "https://example.com/public",
        "WebsiteArchiveBot",
    )

    assert not allowed(
        robots,
        "https://example.com/private",
        "WebsiteArchiveBot",
    )


def test_allowed_allows_when_no_robots_parser():
    assert allowed(
        None,
        "https://example.com/private",
        "WebsiteArchiveBot",
    )


def test_allowed_handles_parser_exception():
    class BrokenRobots:
        def can_fetch(self, user_agent, url):
            raise RuntimeError("robots failure")

    assert allowed(
        BrokenRobots(),
        "https://example.com/page",
        "WebsiteArchiveBot",
    )
