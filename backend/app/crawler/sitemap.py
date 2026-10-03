import httpx
from xml.etree import ElementTree as ET

def urls(txt):
    try:
        root=ET.fromstring(txt)
        return [x.text.strip() for x in root.iter() if x.tag.rsplit("}",1)[-1]=="loc" and x.text]
    except:return []

def get(url,head):
    try:
        r=httpx.get(url,headers=head,timeout=20,follow_redirects=True)
        return r.text if r.status_code<400 else ""
    except:return ""
