from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import hashlib

def norm(url):
    try:
        p=urlsplit(url.strip())
        if p.scheme not in ("http","https") or not p.netloc:return None
        host=p.hostname.lower()
        port=p.port
        net=host
        if port and not ((p.scheme=="http" and port==80) or (p.scheme=="https" and port==443)):net=f"{host}:{port}"
        path=p.path or "/"
        q=[x for x in parse_qsl(p.query,keep_blank_values=True) if not x[0].lower().startswith(("utm_","fbclid","gclid"))]
        return urlunsplit((p.scheme.lower(),net,path,urlencode(q,doseq=True),""))
    except:return None

def host(url):
    try:return urlsplit(url).hostname.lower()
    except:return ""

def key(url):
    return hashlib.sha256(url.encode()).hexdigest()
