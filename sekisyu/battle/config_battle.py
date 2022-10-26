import dataclasses
from dataclasses import field
from typing import Dict, List, Tuple


@dataclasses.dataclass
class ConfigBattle:
    """
    対局条件を格納する。

    initial_pos_list (list(str)):
        初期局面のリスト。デフォルトは["startpos moves"]。現状sfen形式は非対応

    initial_pos_filename str:
        初期局面のリストが格納されたファイル

    btime (int):
        先手番の持ち時間。デフォルトは0

    wtime (int):
        後手番の持ち時間。デフォルトは0

    inc_time (int):
        フィッシャーの場合の持ち時間の増分

    byoyomi (int):
        秒読みの場合の秒読み時間

    time_by_player (bool):
        プレイヤー毎に持ち時間を決めるオプション（持ち時間依存性などを調べるのに使う）

    time_player (int, int):
        各プレイヤーの持ち時間

    inc_player (int, int):
        フィッシャーの場合の各プレイヤーの持ち時間の増分

    byoyomi_player (int, int):
        プレイヤー別の秒読み

    moves_to_draw int:
        最大手数

    lose_timeup bool:
        持ち時間がなくなった場合負けにする

    virtual_delay float:
        通信時間の仮想値

    description str:
        棋戦名をここに書く

    tags list(str):
        データベース登録時に加えるタグ
    """

    initial_pos_list: List[str] = field(default_factory=list)
    initial_pos_filename = ""
    btime: int = 0
    wtime: int = 0
    inc_time: int = 0
    byoyomi: int = 0

    # エンジン別に持ち時間を決めたいとき
    time_by_player: bool = False
    time_player: Tuple[int, int] = (0, 0)
    inc_player: Tuple[int, int] = (0, 0)
    byoyomi_player: Tuple[int, int] = (0, 0)

    # 最大手数
    moves_to_draw: int = 320

    # 時間切れ＝負け
    lose_timeup: bool = False

    # 遅延時間
    virtual_delay: float = 0.0

    description: str = ""

    # 対局の属性
    tags: List[str] = field(default_factory=list)

    def to_dict(self, exclude_initial_pos_list: bool = True) -> Dict:
        """
        対局情報をdictにして出力する

        Args:
            exclude_initial_pos_list: initial_pos_listを除く

        Returns:
            dict : 対局情報のdict
        """
        out = {
            "initial_pos_filename": self.initial_pos_filename,
            "btime": self.btime,
            "wtime": self.wtime,
            "inc_time": self.inc_time,
            "byoyomi": self.byoyomi,
            "time_by_player": self.time_by_player,
            "time_player": self.time_player,
            "inc_player": self.inc_player,
            "byoyomi_player": self.byoyomi_player,
            "moves_to_draw": self.moves_to_draw,
            "lose_timeup": self.lose_timeup,
            "virtual_delay": self.virtual_delay,
            "description": self.description,
        }

        if exclude_initial_pos_list:
            return out
        out["initial_pos_list"] = self.initial_pos_list
        return out
