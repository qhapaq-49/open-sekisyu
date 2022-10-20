import dataclasses
from typing import Any, Dict


@dataclasses.dataclass
class Difficulty:

    infos: Dict[str, Any]
    version: str = "0.0.0"
    # 浅い読みの評価値の差分
    value_diff: int = 0
    null_diff: int = 0
    # 局面が王手の場合（null_diffには代打として1位と2位の評価値の差が入る
    is_check: bool = False
