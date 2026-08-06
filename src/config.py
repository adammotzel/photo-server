from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    name: str
    db_password: SecretStr
    network_name: str
    db_host: str
    db_port: int
    db_user: str
    db_name: str
