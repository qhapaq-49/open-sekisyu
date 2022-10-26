import shogi


def draw_check_from_go_cmd(pos_cmd: str) -> bool:
    """
    goコマンドに送られた内容から引き分け判定を行う
    python-shogiをつかって出てきた局面をsfenにしてsetを作って云々でやるべきか、やねうら王の機能を使うべきかは要検証
    とりあえず動けばよかろうでpython-shogiで雑に判定する
    """
    assert "startpos" in pos_cmd
    try:
        board = shogi.Board()
        moves = pos_cmd.split(" ")
        if len(moves) < 3:
            return False
        moves = moves[3:]
        for move in moves:
            board.push_usi(move)
        result = board.is_fourfold_repetition()
        if result:
            print("found inf loop", pos_cmd)
    except Exception:
        print("bad move found", pos_cmd)
        return False
    return result
