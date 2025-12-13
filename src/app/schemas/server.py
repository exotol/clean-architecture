from pydantic import BaseModel


class ServerConfig(BaseModel):
    host: str
    port: int
    workers: int
    reload: bool
    target_run: str
    factory: bool
    log_level: str
    log_access: bool
