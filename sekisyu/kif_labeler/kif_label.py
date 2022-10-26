import dataclasses


@dataclasses.dataclass
class KifLabel:
    name: str
    description: str = ""
