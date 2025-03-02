from pydantic import BaseModel

class Settings(BaseModel):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "crm_leandro"