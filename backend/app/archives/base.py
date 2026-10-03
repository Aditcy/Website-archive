from dataclasses import dataclass

@dataclass
class Res:
    ok:bool
    url:str|None=None
    aid:str|None=None
    err:str|None=None

class Arch:
    name="base"
    def submit(self,url):raise NotImplementedError
    def status(self,aid):raise NotImplementedError
