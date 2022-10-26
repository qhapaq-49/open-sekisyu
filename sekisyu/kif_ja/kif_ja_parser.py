from typing import List

import shogi
from sekisyu.board.get_board_from_pos_cmd import get_board_from_pos_cmd

PIECE_STR_JA = [
    "",
    "歩",
    "香",
    "桂",
    "銀",
    "金",
    "角",
    "飛",
    "王",
    "と",
    "成香",
    "成桂",
    "成銀",
    "馬",
    "竜",
]


def get_ja_move(board: shogi.Board, move_usi, prev_move_usi: str = None):
    out = ""
    is_drop = False
    try:
        move = shogi.Move.from_usi(move_usi)
    except Exception:
        print(
            f"info string {move_usi} is unknown movetype possibly because of update of usi protocol"
        )
        return None
    if move.from_square is None:
        is_drop = True
        out += str(9 - move.to_square % 9) + str(1 + move.to_square // 9)
        out += PIECE_STR_JA[move.drop_piece_type]
    else:
        is_recapture = False
        if prev_move_usi is not None:
            prev_move = shogi.Move.from_usi(prev_move_usi)
            if move.to_square == prev_move.to_square:
                is_recapture = True
        if is_recapture:
            out += "同"
        else:
            out += str(9 - move.to_square % 9) + str(1 + move.to_square // 9)
        out += PIECE_STR_JA[board.piece_type_at(move.from_square)]
        if move.promotion:
            out += "成"

    if is_drop:
        out += "打"

    if board.turn == shogi.BLACK:
        out = "▲" + out
    else:
        out = "△" + out
    return out


def translate_pv(current_pos: str, moves: List[str], prev_move: str = None) -> str:
    """
    盤面とpvから日本語の棋譜を取得する

    current_pos(str) : 現局面のpos_cmd
    moves(list(str)) : usi形式のpv
    prev_move (str) : この局面に入る前に指された手(同hogeの処理に使う)
    """
    board = get_board_from_pos_cmd(current_pos)
    # board from current pos
    out = ""
    prev = prev_move
    move_num = 0
    for i, move in enumerate(moves):
        jmove = get_ja_move(board, move, prev)
        if jmove is None:
            break
        out += jmove + "、"
        board.push_usi(move)
        prev = move
        move_num += 1

    for _ in range(move_num):
        board.pop()

    return out[:-1]
