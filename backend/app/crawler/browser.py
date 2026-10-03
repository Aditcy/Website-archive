def render(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        pg=b.new_page()
        pg.goto(url,wait_until="networkidle",timeout=60000)
        txt=pg.content()
        b.close()
        return txt
