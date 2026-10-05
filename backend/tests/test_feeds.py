from app.crawler.feeds import find


def test_find_rss_feed():
    html = """
    <html>
      <head>
        <link
          rel="alternate"
          type="application/rss+xml"
          href="/feed.xml"
        >
      </head>
    </html>
    """

    assert find(
        html,
        "https://example.com/page",
    ) == [
        "https://example.com/feed.xml",
    ]


def test_find_atom_feed():
    html = """
    <html>
      <head>
        <link
          rel="alternate"
          type="application/atom+xml"
          href="/atom.xml"
        >
      </head>
    </html>
    """

    assert find(
        html,
        "https://example.com/page",
    ) == [
        "https://example.com/atom.xml",
    ]


def test_find_absolute_feed():
    html = """
    <link
      rel="alternate"
      type="application/rss+xml"
      href="https://feeds.example.com/feed.xml"
    >
    """

    assert find(
        html,
        "https://example.com/",
    ) == [
        "https://feeds.example.com/feed.xml",
    ]


def test_find_ignores_normal_stylesheets():
    html = """
    <html>
      <head>
        <link rel="stylesheet" href="/style.css">
      </head>
    </html>
    """

    assert find(
        html,
        "https://example.com/",
    ) == []


def test_find_handles_multiple_feeds():
    html = """
    <html>
      <head>
        <link rel="alternate" type="application/rss+xml" href="/rss.xml">
        <link rel="alternate" type="application/atom+xml" href="/atom.xml">
      </head>
    </html>
    """

    assert find(
        html,
        "https://example.com/",
    ) == [
        "https://example.com/rss.xml",
        "https://example.com/atom.xml",
    ]
