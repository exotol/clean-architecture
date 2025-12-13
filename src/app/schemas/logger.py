from pydantic import BaseModel


class LoggerConfig(BaseModel):
    log_level: str
    log_format: str
