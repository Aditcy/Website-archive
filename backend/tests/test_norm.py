from app.crawler.normalize import norm

def test_norm():
    assert norm("https://EXAMPLE.com/a#x")=="https://example.com/a"
    assert norm("https://example.com/a?utm_source=x&x=1")=="https://example.com/a?x=1"
