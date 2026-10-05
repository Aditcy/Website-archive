from bs4 import BeautifulSoup
from urllib.parse import urljoin

def find(txt,base):
    s=BeautifulSoup(txt,"html.parser")
    out=[]
    for x in s.find_all(["link"],href=True):
        t=(x.get("type") or "").lower()
        if "rss" in t or "atom" in t or "feed" in t:out.append(urljoin(base,x["href"]))
    return out
