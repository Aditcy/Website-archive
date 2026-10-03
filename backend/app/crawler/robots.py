from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

def read(base):
    u=urljoin(base,"/robots.txt")
    try:
        r=RobotFileParser(u);r.read();return r
    except:return None

def maps(txt):
    return [x.split(":",1)[1].strip() for x in txt.splitlines() if x.lower().startswith("sitemap:")]
