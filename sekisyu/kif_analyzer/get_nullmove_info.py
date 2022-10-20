from typing import Tuple

import shogi
from sekisyu.board.get_board_from_pos_cmd import get_board_from_pos_cmd
from sekisyu.engine.base_engine import BaseEngine
from sekisyu.playout.playinfo import BasePlayInfoPack


def get_nullmove_info(
    engine: BaseEngine, pos_cmd: str, go_cmd: str
) -> Tuple[str, BasePlayInfoPack]:
    """
    パスした場合の盤面評価を得る。仮にmateがでるならその局面はつめろ

    engine (BaseEngine) : 局面解析に使うエンジン
    pos_cmd (str) : 解析する局面。usiのpositionコマンドの文字列
    go_cmd (str) : エンジンに与えるコマンド

    return:
        nullmove後の局面のgo_cmdと解析結果
    """

    board = get_board_from_pos_cmd(pos_cmd)
    if board.turn == shogi.BLACK:
        board.turn = shogi.WHITE
    else:
        board.turn = shogi.BLACK

    sfen_cmd = f"position sfen {board.sfen()}"
    # print(sfen_cmd)
    engine.send_command(sfen_cmd)
    # print(go_cmd)
    return sfen_cmd, engine.send_go_and_wait(go_cmd)
