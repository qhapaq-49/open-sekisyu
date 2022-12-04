from typing import Optional

import shogi.CSA
from shogi import Board

COLORS = [BLACK, WHITE] = range(2)
SQUARES = [
    A9,
    A8,
    A7,
    A6,
    A5,
    A4,
    A3,
    A2,
    A1,
    B9,
    B8,
    B7,
    B6,
    B5,
    B4,
    B3,
    B2,
    B1,
    C9,
    C8,
    C7,
    C6,
    C5,
    C4,
    C3,
    C2,
    C1,
    D9,
    D8,
    D7,
    D6,
    D5,
    D4,
    D3,
    D2,
    D1,
    E9,
    E8,
    E7,
    E6,
    E5,
    E4,
    E3,
    E2,
    E1,
    F9,
    F8,
    F7,
    F6,
    F5,
    F4,
    F3,
    F2,
    F1,
    G9,
    G8,
    G7,
    G6,
    G5,
    G4,
    G3,
    G2,
    G1,
    H9,
    H8,
    H7,
    H6,
    H5,
    H4,
    H3,
    H2,
    H1,
    I9,
    I8,
    I7,
    I6,
    I5,
    I4,
    I3,
    I2,
    I1,
] = range(81)

bw_txt = ["先手", "後手"]

PIECE_CHARA = [
    [
        NONE,
        PAWN,
        LANCE,
        KNIGHT,
        SILVER,
        GOLD,
        BISHOP,
        ROOK,
        KING,
        PROM_PAWN,
        PROM_LANCE,
        PROM_KNIGHT,
        PROM_SILVER,
        PROM_BISHOP,
        PROM_ROOK,
    ],
    [
        NONE,
        PAWN,
        LANCE,
        KNIGHT,
        SILVER,
        GOLD,
        BISHOP,
        ROOK,
        KING,
        PROM_PAWN,
        PROM_LANCE,
        PROM_KNIGHT,
        PROM_SILVER,
        PROM_BISHOP,
        PROM_ROOK,
    ],
] = [
    [".", "P", "L", "N", "S", "G", "B", "R", "K", "+P", "+L", "+N", "+S", "+B", "+R"],
    [".", "p", "l", "n", "s", "g", "b", "r", "k", "+p", "+l", "+n", "+s", "+b", "+r"],
]


PIECE_TYPE = [
    NONE,
    PAWN,
    LANCE,
    KNIGHT,
    SILVER,
    GOLD,
    BISHOP,
    ROOK,
    KING,
    PROM_PAWN,
    PROM_LANCE,
    PROM_KNIGHT,
    PROM_SILVER,
    PROM_BISHOP,
    PROM_ROOK,
] = [  # type:ignore
    i for i in range(15)
]

PIECE_STR_CSA = [
    "",
    "FU",
    "KY",
    "KE",
    "GI",
    "KI",
    "KA",
    "HI",
    "OU",
    "TO",
    "NY",
    "NK",
    "NG",
    "UM",
    "RY",
]


def have_piece(board: Board, color: int, piece: int) -> bool:
    return PIECE_TYPE[piece] in board.pieces_in_hand[color]


def is_piece(board: Board, color: int, piece: int, sq: int) -> bool:
    return (
        conv_piece_to_str(board.piece_at(get_square(color, sq)))
        == PIECE_CHARA[color][PIECE_TYPE[piece]]
    )


def get_square(color: int, sq: int) -> int:
    if color == 0:
        return SQUARES[sq]
    else:
        return 80 - SQUARES[sq]


def conv_piece_to_str(piece: Optional[int]) -> str:
    if piece is None:
        return "."
    else:
        return piece.symbol()  # type:ignore


def promote_piece(piece_id: int) -> int:
    if piece_id <= GOLD:  # type:ignore
        return piece_id + 8
    return piece_id + 7


def get_csa_move(board: Board, move_usi: str, is_black: bool = True) -> str:
    out = ""
    try:
        move = shogi.Move.from_usi(move_usi)
    except ValueError:
        return move_usi

    if move.from_square is None:
        out += "00"
        out += str(9 - move.to_square % 9) + str(1 + move.to_square // 9)
        out += PIECE_STR_CSA[move.drop_piece_type]
    else:
        out += (
            str(9 - move.from_square % 9)
            + str(1 + move.from_square // 9)
            + str(9 - move.to_square % 9)
            + str(1 + move.to_square // 9)
        )
        if move.promotion:
            out += PIECE_STR_CSA[promote_piece(board.piece_type_at(move.from_square))]
        else:
            out += PIECE_STR_CSA[board.piece_type_at(move.from_square)]

    if is_black:
        out = "+" + out
    else:
        out = "-" + out
    return out


if __name__ == "__main__":
    board = shogi.Board()
    print(get_csa_move(board, "2g2f"))
    print(get_csa_move(board, "7g7f"))
