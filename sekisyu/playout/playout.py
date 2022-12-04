import dataclasses
import json
from dataclasses import field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

import shogi
from dacite import Config, from_dict
from sekisyu.battle.config_battle import ConfigBattle
from sekisyu.board.mycsa import Parser
from sekisyu.kif_analyzer.config_kif_analyzer import ConfigAnalysis
from sekisyu.kif_labeler.game_info_getter import get_title_alias_year_csa
from sekisyu.playout.playinfo import BasePlayInfo, BasePlayInfoPack
from shogi import KIF


# ゲームの終局状態を示す
class GameResult(IntEnum):
    BLACK_WIN = 0  # 先手勝ち
    WHITE_WIN = 1  # 後手勝ち
    DRAW = 2  # 千日手引き分け(現状、サポートしていない)
    MAX_MOVES = 3  # 最大手数に到達
    BLACK_ILLEGAL_MOVE = 4  # 反則の指し手が出た
    WHITE_ILLEGAL_MOVE = 5  # 反則の指し手が出た
    BLACK_TIMEUP = 6  # 先手時間切れ
    WHITE_TIMEUP = 7  # 後手時間切れ
    BLACK_DECLARE = 8  # 先手宣言勝ち
    WHITE_DECLARE = 9  # 後手宣言勝ち
    DRAW_DECLARE = 10  # 持将棋
    INIT = 11  # ゲーム開始前
    PLAYING = 12  # まだゲーム中
    STOP_GAME = 13  # 強制stopさせたので結果は保証されず

    # turn側が投了したときの定数を返す
    @staticmethod
    def from_resign(turn: int) -> int:  # GameResult(IntEnum)
        return GameResult.WHITE_WIN if turn == 0 else GameResult.BLACK_WIN

    # turn側が違法手をしたときの定数を返す
    @staticmethod
    def from_illeagal(turn: int) -> int:  # GameResult(IntEnum)
        return (
            GameResult.BLACK_ILLEGAL_MOVE
            if turn == 0
            else GameResult.WHITE_ILLEGAL_MOVE
        )

    # turn側が宣言勝ちしたときの定数を返す
    @staticmethod
    def from_declare(turn: int) -> int:  # GameResult(IntEnum)
        return GameResult.BLACK_DECLARE if turn == 0 else GameResult.WHITE_DECLARE

    # turn側が時間切れしたときの定数を返す
    @staticmethod
    def from_timeup(turn: int) -> int:  # GameResult(IntEnum)
        return GameResult.BLACK_TIMEUP if turn == 0 else GameResult.WHITE_TIMEUP

    # ゲームは引き分けであるのか？
    def is_draw(self) -> bool:
        return (
            self == GameResult.DRAW
            or self == GameResult.MAX_MOVES
            or self == GameResult.DRAW_DECLARE
        )

    # 先手が勝利したか？
    def is_black_win(self) -> bool:
        return (
            self == GameResult.BLACK_WIN
            or self == GameResult.BLACK_DECLARE
            or self == GameResult.WHITE_TIMEUP
            or self == GameResult.WHITE_ILLEGAL_MOVE
        )

    # 後手が勝利したか？
    def is_white_win(self) -> bool:
        return (
            self == GameResult.WHITE_WIN
            or self == GameResult.WHITE_DECLARE
            or self == GameResult.BLACK_TIMEUP
            or self == GameResult.BLACK_ILLEGAL_MOVE
        )

    # ゲームの決着がついているか？
    def is_gameover(self) -> bool:
        return self != GameResult.INIT and self != GameResult.PLAYING

    def __str__(self) -> str:
        if self == GameResult.BLACK_WIN:
            return "black_win"
        elif self == GameResult.WHITE_WIN:
            return "white_win"
        elif self == GameResult.DRAW:
            return "draw"
        elif self == GameResult.MAX_MOVES:
            return "max_moves"
        elif self == GameResult.BLACK_ILLEGAL_MOVE:
            return "black_illegal"
        elif self == GameResult.WHITE_ILLEGAL_MOVE:
            return "white_illegal"
        elif self == GameResult.BLACK_TIMEUP:
            return "black_timeup"
        elif self == GameResult.WHITE_TIMEUP:
            return "white_timeup"
        elif self == GameResult.BLACK_DECLARE:
            return "black_declare"
        elif self == GameResult.WHITE_DECLARE:
            return "white_declare"
        return "illegal_game"


@dataclasses.dataclass
class BasePlayOut:
    """
    対局結果と対局中の情報を格納する

    plys (list(str)):
        指し手のリスト

    engine_option (tuple(list(tuple(str,str)), list(tuple(str,str)))):
        対局したエンジンの情報。setoptionのnameとvalueに相当。数字やboolのデータも文字列にすることに注意

    initial_pos (str):
        初期局面。デフォルトはstartpos。sfen形式

    playinfo_list (list(BasePlayInfoPack)):
        局面の読み筋。

    evalinfo_list (list(BasePlayInfoPack)):
        局面の解析結果。

    timestamp (str):
        対局日、時間

    player_name Tuple[str, str]:
        対局者の名前(先手、 後手)

    game_config ConfigBattle:
        対局の設定。AI同士の自己対局の場合ここに設定が入る

    result (GameResult):
        対局結果

    tags (list(str)):
        棋譜の属性

    config_analysis (ConfigAnalysis):
        解析データがある際の解析エンジンの設定
    """

    engine_option: Tuple[List[Tuple[str, str]], List[Tuple[str, str]]] = ([], [])
    plys: List[str] = field(default_factory=list)
    player_name: Tuple[str, str] = ("", "")
    initial_pos: str = "startpos"
    playinfo_list: List[BasePlayInfoPack] = field(default_factory=list)
    evalinfo_list: List[BasePlayInfoPack] = field(default_factory=list)
    timestamp: str = ""
    game_config: ConfigBattle = ConfigBattle()
    result: GameResult = GameResult.PLAYING
    tags: Optional[List[str]] = field(default_factory=list)
    config_analysis: Optional[ConfigAnalysis] = None

    def to_dict(self) -> None:
        """
        棋譜情報をdictにして保存する
        """
        return {
            "player_name": self.player_name,
            "engine_option": self.engine_option,
            "player_black": self.player_name[0],
            "option_black": self.engine_option[0],
            "player_white": self.player_name[1],
            "option_white": self.engine_option[1],
            "timestamp": self.timestamp,
            "initial_pos": self.initial_pos,
            "plys": self.plys,
            "playinfo_list": [info.to_dict() for info in self.playinfo_list],
            "evalinfo_list": [info.to_dict() for info in self.evalinfo_list],
            "config_battle": self.game_config.to_dict(),
            "result": self.result,
            "result_str": str(self.result),
            "tags": self.tags,
            "config_analysis": None
            if self.config_analysis is None
            else dataclasses.asdict(self.config_analysis),
        }

    def to_json(self, file_name: str) -> None:
        """
        jsonファイルを出力する

        Args:
            file_name (str) : 出力するファイル名
        """
        with open(file_name, "w") as f:
            json.dump(
                self.to_dict(),
                f,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
                separators=(",", ": "),
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        dictからplayoutを生成する

        Args:
            file_name (dict) : 辞書データ

        Returns:
            BasePlayOut : 生成されたplayout
        """
        if "config_analysis" in data and data["config_analysis"] == "None":
            data["config_analysis"] = None
        return from_dict(
            data_class=BasePlayOut, data=data, config=Config(cast=[tuple, int, str])
        )

    @classmethod
    def from_csa(cls, file_name: str):
        """
        csaファイルからplayoutを生成する

        Args:
            file_name (str) : 読み込みファイル名

        Returns:
            BasePlayOut : 生成されたplayout
        """
        csa_dat = Parser.parse_file(file_name)[0]
        idx = 0
        info_pack_list = []
        for pvs, values in zip(csa_dat["pvs"], csa_dat["values"]):
            infos = []
            for pv, value in zip(pvs, values):
                pv_to_use = [csa_dat["moves"][idx]]
                pv_to_use.extend(pv)
                playinfo = BasePlayInfo(
                    pv=pv_to_use, eval=value if idx % 2 == 0 else -value
                )
                infos.append(playinfo)
                break  # csa does not support multipv
            info_pack = BasePlayInfoPack(infos=infos)
            idx += 1
            info_pack_list.append(info_pack)

        alias, timestamp, title = get_title_alias_year_csa(file_name)
        if csa_dat["win"] == "b":
            result = GameResult.BLACK_WIN
        elif csa_dat["win"] == "w":
            result = GameResult.WHITE_WIN
        else:
            result = GameResult.DRAW
        output = cls.from_dict(
            {
                "plys": csa_dat["moves"],
                "player_name": (
                    csa_dat["names"][shogi.BLACK],
                    csa_dat["names"][shogi.WHITE],
                ),
                "timestamp": timestamp,
                "result": result,
            }
        )
        output.playinfo_list = info_pack_list
        return output

    @classmethod
    def from_kif(cls, file_name: str):
        """
        kifファイルからplayoutを生成する

        Args:
            file_name (str) : 読み込みファイル名

        Returns:
            BasePlayOut : 生成されたplayout
        """
        csa_dat = KIF.Parser.parse_file(file_name)[0]
        if csa_dat["win"] == "b":
            result = GameResult.BLACK_WIN
        elif csa_dat["win"] == "w":
            result = GameResult.WHITE_WIN
        else:
            result = GameResult.DRAW
        return cls.from_dict(
            {
                "plys": csa_dat["moves"],
                "player_name": (
                    csa_dat["names"][shogi.BLACK],
                    csa_dat["names"][shogi.WHITE],
                ),
                "result": result,
            }
        )
