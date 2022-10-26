import dataclasses
from typing import Any, Dict

from sekisyu.battle.config_battle import ConfigBattle


@dataclasses.dataclass
class ConfigAutoBattle:
    # 対局の設定
    config: ConfigBattle
    # 1pのconfig
    config_1p: Dict[str, Any]
    # 2pのconfig
    config_2p: Dict[str, Any]
    # 対局回数
    battle_num: int = 100
    # 対局結果を出力する頻度
    print_interval: int = 1
    # 棋譜の保存先+prefix
    kif_prefix: str = ""
    # 試合ごとに先後を入れ替える
    flip: bool = True
    # playoutのjsonを保存する
    save_json: bool = True
    # playoutのcsaを保存する
    save_csa: bool = True


@dataclasses.dataclass
class AutoBattleResult:
    win_1p_black: int = 0
    win_1p_white: int = 0
    draw_1p_black: int = 0
    draw_1p_white: int = 0
    win_2p_black: int = 0
    win_2p_white: int = 0
