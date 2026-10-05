from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin


def read(base):
    url = urljoin(base, "/robots.txt")

    try:
        parser = RobotFileParser()
        parser.set_url(url)
        parser.read()
        return parser
    except Exception:
        return None


def allowed(parser, url, user_agent):
    if parser is None:
        return True

    try:
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True


def maps(txt):
    result = []

    for line in txt.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.lower().startswith("sitemap:"):
            value = line.split(":", 1)[1].strip()

            if value:
                result.append(value)

    return result
