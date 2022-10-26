import shogi
from sekisyu.csa.csa_parser import get_csa_move
from sekisyu.playout.playout import BasePlayOut

csa_initial_board = "P1-KY-KE-GI-KI-OU-KI-GI-KE-KY\nP2 * -HI *  *  *  *  * -KA * \nP3-FU-FU-FU-FU-FU-FU-FU-FU-FU\nP4 *  *  *  *  *  *  *  *  * \nP5 *  *  *  *  *  *  *  *  * \nP6 *  *  *  *  *  *  *  *  * \nP7+FU+FU+FU+FU+FU+FU+FU+FU+FU\nP8 * +KA *  *  *  *  * +HI * \nP9+KY+KE+GI+KI+OU+KI+GI+KE+KY\n+\n"  # noqa


def playout_to_csa_v22(playout: BasePlayOut, file_name: str):
    """
    v2.2のcsaを出力する

    Args:
        playout (BasePlayOut) : csaにするplayout

        file_name (str): 出力するcsaファイル名
    """
    out = "V2.2\n"
    out += "N+" + playout.player_name[0] + "\nN-" + playout.player_name[1] + "\n"
    out += (
        "'Max_Moves:"
        + str(playout.game_config.moves_to_draw)
        + "\n'Least_Time_Per_Move:0\n'Increment:"
        + str(playout.game_config.inc_time)
        + "\n$EVENT:"
        + playout.game_config.description
        + "\n$START_TIME:"
        + playout.timestamp
        + "\n"
    )
    out += csa_initial_board
    moves = playout.plys
    board = shogi.Board()
    for i, move_str in enumerate(moves):
        if move_str == "resign" or move_str == "win":
            break
        # 指し手
        csa_move = get_csa_move(board, move_str, i % 2 == 0)
        out += csa_move + "\n"

        # 読み筋
        info_id = i - len(playout.initial_pos.split(" ")) + 3
        if info_id >= 0 and len(playout.playinfo_list) > info_id:
            info = playout.playinfo_list[info_id]
            if len(info.infos) > 0:
                if i % 2 == 0:
                    pv_line = "'** " + str(info.infos[0].eval) + " "
                else:
                    pv_line = "'** " + str(-info.infos[0].eval) + " "
                pop_cnt = 0
                for j, ply in enumerate(info.infos[0].pv):
                    # csaの前時代的な表記方法に従うとこうなるらしい。
                    if j > 0:
                        pv_line += get_csa_move(board, ply, (i + j) % 2 == 0) + " "
                    try:
                        move = shogi.Move.from_usi(ply)
                    except ValueError:
                        break
                    try:
                        board.push(move)
                        pop_cnt += 1
                    except ValueError:
                        print(
                            playout.plys, playout.plys[i], info.infos[0].pv, ply, board
                        )
                        raise ValueError

                for _ in range(pop_cnt):
                    board.pop()
                out += pv_line + "\n"
        board.push(shogi.Move.from_usi(move_str))

    if playout.result.is_draw():
        out += "%HIKIWAKE"
    else:
        out += "%TORYO"
    with open(file_name, "w") as f:
        f.write(out)
