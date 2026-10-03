from bs4 import BeautifulSoup
from urllib.parse import urljoin

def links(txt,base):
    s=BeautifulSoup(txt,"html.parser")
    out=[]
    for a in s.find_all("a",href=True):
        u=urljoin(base,a["href"])
        out.append(u)
    for x in s.find_all("link",href=True):
        r=x.get("rel",[])
        if "canonical" in [str(i).lower() for i in r]:out.append(urljoin(base,x["href"]))
    return out
