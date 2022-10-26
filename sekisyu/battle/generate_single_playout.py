from typing import List, Optional

from sekisyu.engine.base_engine import BaseEngine
from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.playout.playout import BasePlayOut


def generate_single_playout(
    start_pos: str,
    engine1: BaseEngine,
    engine2: BaseEngine,
    go_cmd: str = "go nodes 10000",
    move_exclude: Optional[List[str]] = None,
    max_move: int = 256,
) -> BasePlayOut:
    """
    指定した局面で対局を一度だけ行いplayoutを返す
    棋譜解析などの名目でこれをよく使うので別の関数にする

    Args:
        start_pos (str) : 開始局面

    Returns
        BasePlayOut : プレイアウト
    """
    playout = BasePlayOut(
        engine_option=(engine1.get_option(), engine1.get_option()),
        initial_pos=start_pos,
        timestamp="",
        player_name=(engine1.get_name(), engine2.get_name()),
    )
    current_pos = start_pos
    for i in range(max_move):
        if i % 2 == 0:
            engine = engine1
        else:
            engine = engine2
        engine.send_command(current_pos)
        play_info: BasePlayInfoPack = engine.send_go_and_wait(go_cmd)
        if move_exclude:
            fail_exclude = True
            for info in play_info.infos:
                if info.pv[0] not in move_exclude:
                    play_info.bestmove = info.pv[0]
                    fail_exclude = False
                    break
            if fail_exclude:
                break
        playout.playinfo_list.append(play_info.copy())
        if play_info.bestmove == "resign":
            break
        playout.plys.append(play_info.bestmove)
        current_pos += " " + play_info.bestmove
    return playout
