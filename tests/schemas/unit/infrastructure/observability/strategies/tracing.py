from dataclasses import dataclass


@dataclass
class StartSpanEntity:
    name: str

@dataclass
class StartSpanExpected:
    tracer_called_with: str
    kind_attr: str
