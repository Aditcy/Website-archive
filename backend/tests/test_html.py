from app.crawler.html import links


def test_links_finds_absolute_links():
    html = """
    <html>
        <body>
            <a href="https://example.com/about">About</a>
        </body>
    </html>
    """

    assert links(
        html,
        "https://example.com/",
    ) == ["https://example.com/about"]


def test_links_resolves_relative_links():
    html = """
    <a href="/about">About</a>
    <a href="contact">Contact</a>
    """

    result = links(
        html,
        "https://example.com/docs/page",
    )

    assert "https://example.com/about" in result
    assert "https://example.com/docs/contact" in result


def test_links_finds_canonical():
    html = """
    <link rel="canonical" href="/preferred">
    """

    result = links(
        html,
        "https://example.com/page",
    )

    assert "https://example.com/preferred" in result


def test_links_ignores_non_href_elements():
    html = """
    <a>No href</a>
    <div href="/fake">Fake</div>
    <script src="/script.js"></script>
    """

    assert links(
        html,
        "https://example.com/",
    ) == []


def test_links_handles_fragments():
    html = """
    <a href="/page#section">Section</a>
    """

    result = links(
        html,
        "https://example.com/",
    )

    assert result == ["https://example.com/page#section"]


def test_links_handles_malformed_html():
    html = """
    <html>
        <body>
            <a href="/one">One
            <a href="/two"><b>Two
            <div>
        </body>
    """

    result = links(
        html,
        "https://example.com/",
    )

    assert "https://example.com/one" in result
    assert "https://example.com/two" in result
