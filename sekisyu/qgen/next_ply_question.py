import dataclasses
from typing import List, Optional

from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.qgen.question_evaluator import Difficulty


@dataclasses.dataclass
class NextPlyQuestion:
    # usiプロトコルの出題局面
    question_pos: str
    # 出題盤面のsfen
    question_sfen: str
    # 答え（もとい、ソフトの解析結果）
    playinfo: BasePlayInfoPack
    # usiプロトコルのpos
    before_pos: Optional[str] = None
    # usiプロトコルのpv
    before_pv: Optional[str] = None
    # 選択肢（usi）
    selection_usi: Optional[List[str]] = None
    # 評価値
    values: Optional[List[int]] = None
    # 選択肢（日本語）
    selection_ja: Optional[List[str]] = None
    # 評価値（日本語）
    pv_value_ja: Optional[List[str]] = None
    # pvの局面のsfen
    pv_sfen: Optional[List[List[str]]] = None

    # engine_name
    engine_name: Optional[str] = None
    # ユーザが書き込めるmemo。メモで検索などを可能にしたい
    memo: str = ""
    # 作成したsekisyuのバージョン
    version: str = "1.0.0"

    # 棋譜で指された手
    ply_answer: str = ""

    # 正解を生成するために用いたgo_cmd
    go_cmd_ans: str = ""

    # 難易度測定のために用いたgo_cmd
    go_cmd_calc: str = ""
    play_info_calc: Optional[BasePlayInfoPack] = None

    # パスした場合の評価
    null_move_info: Optional[BasePlayInfoPack] = None
    null_ans_list: Optional[List[str]] = None
    null_sfen_list: Optional[List[List[str]]] = None
    null_value_list: Optional[List[int]] = None

    # 自分の指し手に対して相手がパスした場合の評価
    null_enemy_move_info: Optional[List[BasePlayInfoPack]] = None
    null_enemy_ans_list: Optional[List[str]] = None
    null_enemy_sfen_list: Optional[List[List[str]]] = None
    null_enemy_value_list: Optional[List[int]] = None

    difficulty: Optional[Difficulty] = None
