from pydantic import BaseModel

class SubOut(BaseModel):
    id:int
    service:str
    status:str
    archive_url:str|None
    tries:int
    error:str|None
    model_config={"from_attributes":True}
