from urllib.parse import quote
from .base import Arch,Res

class Arc(Arch):
    name="archive_today"
    def submit(self,url):
        u=f"https://archive.today/?run=1&url={quote(url,safe='')}"
        return Res(False,url=u,err="manual_required")
    def status(self,aid):return {}
