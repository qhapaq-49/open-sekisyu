import shogi


def get_board_from_pos_cmd(pos_cmd: str) -> shogi.Board:
    sfen_id = pos_cmd.find("sfen")
    moves_id = pos_cmd.find("moves")

    if sfen_id != -1:
        if moves_id != -1:
            sfen = pos_cmd[sfen_id + 5 : moves_id]
        else:
            sfen = pos_cmd[sfen_id + 5 :]
        board = shogi.Board(sfen=sfen)
    else:
        board = shogi.Board()
    if moves_id != -1:
        moves = pos_cmd[moves_id + 6 :].split(" ")
        for move in moves:
            if move != "":
                board.push_usi(move)
    return board


if __name__ == "__main__":
    print(get_board_from_pos_cmd("position startpos moves"))
    print(get_board_from_pos_cmd("position startpos"))
    print(get_board_from_pos_cmd("position startpos moves 7g7f 3c3d"))
    print(
        get_board_from_pos_cmd(
            "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1 moves 2g2f"
        )
    )
    print(
        get_board_from_pos_cmd(
            "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
        )
    )
