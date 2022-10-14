import dataclasses
from dataclasses import field
from typing import Any, Dict, List, Optional, Tuple


@dataclasses.dataclass
class ConfigEngine:
    """
    エンジンの生成条件

    engine_name (str):
        エンジンの名前

    engine_mode (str):
        エンジンの種類

    engine_path (str):
        エンジンのパス

    option (list(tuple(str, str))):
        エンジンに入れるオプション

    engine_config (dict(str)) :
        予備のオプション。setoptionの外でやりたい設定があるなら
    """

    engine_name: str = ""
    engine_mode: str = ""
    engine_path: str = ""
    option: List[Tuple[str, str]] = field(default_factory=list)
    engine_config: Optional[Dict[str, Any]] = None
