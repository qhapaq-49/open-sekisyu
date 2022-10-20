import random
from typing import List, Optional, Tuple

from sekisyu.board.get_board_from_pos_cmd import get_board_from_pos_cmd
from sekisyu.engine.base_engine import BaseEngine
from sekisyu.kif_analyzer.get_nullmove_info import get_nullmove_info
from sekisyu.kif_ja.kif_ja_parser import translate_pv
from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.qgen.next_ply_question import NextPlyQuestion


def parse_pv_info(
    start_pos_in, infos: BasePlayInfoPack, mv_show: Optional[str] = None
) -> Tuple[List[str], List[List[str]], List[int]]:

    if "moves" not in start_pos_in:
        start_pos = start_pos_in + " moves "
    else:
        start_pos = start_pos_in + " "

    ans_list: List[str] = []
    sfen_list: List[List[str]] = []
    values: List[int] = []

    for info in infos.infos:
        sfen_pv = []
        mv_str = translate_pv(start_pos, [info.pv[0]])
        if mv_show:
            ans = f"{mv_show} 評価値 {info.eval} : "
        else:
            ans = f"{mv_str} 評価値 {info.eval} : "
        ans += translate_pv(start_pos, info.pv)
        values.append(info.eval)
        pv_str = start_pos
        for pv in info.pv:
            pv_str += pv + " "
            sfen_pv.append(get_board_from_pos_cmd(pv_str).sfen())
        sfen_list.append(sfen_pv)
        ans_list.append(ans)

    return ans_list, sfen_list, values


def random_noise_multipv(infos: BasePlayInfoPack, noise: int) -> int:
    """
    局面の多様性を確保するために評価値にランダムノイズを乗せる

    Args:
        info(BasePlayInfoPack) : 読みの情報
        noise(int) : 評価値に乗っけるノイズ

    Returns:
        採択する手の順位
    """
    max_v = -9999
    max_idx = 0
    for i, info in enumerate(infos.infos):
        v = info.eval + random.randint(0, noise)
        if v > max_v:
            max_v = v
            max_idx = i
    return max_idx


def generate_question_from_pos(
    start_pos: str,
    engine: BaseEngine,
    go_cmd: str,
    move_use: int = 1,
    noise_first: int = 334,
    noise_second: int = 334,
    go_cmd_calc: Optional[str] = None,
    go_cmd_null: Optional[str] = None,
    go_cmd_null_enemy: Optional[str] = None,
    null_enemy_rank: Optional[int] = None,
) -> Optional[NextPlyQuestion]:
    """
    特定の局面から類似局面を生成し、次の一手問題を生成する

    Args:
        start_pos(str) : この局面から指し継がせる。usiプロトコルのposition cmd
        engine(BaseEngine) : 検討に使うソフト
        go_cmd(str) : 検討のときに投げるgo_cmd
        move_use(int) : 動かす手数。最低1
        noise_first(int) : 先に動かす側のノイズ
        noise_second(int) : 後に動かす側のノイズ
        go_cmd_calc (str) : 問題の難易度測定向けのエンジンのgo_cmd
        go_cmd_null(str) : パスをした時の変化を測定する際のgo_cmd
        go_cmd_null_enemy (str) : 自分の手に対して相手がパスした時の解析のためのgo_cmd

    Returns:
        NextPlyQuestion : 生成された問題
    """
    engine.send_command(start_pos)
    pv = ""
    for i in range(move_use):
        infos = engine.send_go_and_wait(go_cmd)
        idx = random_noise_multipv(infos, noise_second if i % 2 == 0 else noise_first)
        if i != move_use - 1:
            pv += infos.infos[idx].pv[0] + " "
            # pv += info.infos[0].pv[0] + " "
        engine.send_command(start_pos + " " + pv)
        if infos.infos[idx].pv[0] == "resign" or infos.infos[idx].pv[0] == "win":
            return None

    selection_usi = []
    for info in infos.infos:
        selection_usi.append(info.pv[0])

    info_calc: Optional[BasePlayInfoPack] = None
    if go_cmd_calc:
        info_calc = engine.send_go_and_wait(go_cmd_calc)

    board = get_board_from_pos_cmd(start_pos + " " + pv)

    if not board.is_check() and go_cmd_null:
        null_sfen, null_info = get_nullmove_info(
            engine, start_pos + " " + pv, go_cmd_null
        )
        null_ans_list, null_sfen_list, null_value_list = parse_pv_info(
            null_sfen, null_info
        )
    else:
        null_info = None
        null_ans_list = None
        null_sfen_list = None
        null_value_list = None

    ans_list, sfen_list, value_list = parse_pv_info(start_pos + " " + pv, infos)

    null_enemy_move_info: List[Optional[BasePlayInfoPack]] = []
    null_enemy_ans_list: Optional[List[str]] = []
    null_enemy_sfen_list: Optional[List[List[str]]] = []
    null_enemy_value_list: Optional[List[int]] = []
    if go_cmd_null_enemy:
        for i, info in enumerate(infos.infos):
            if null_enemy_rank and i >= null_enemy_rank:
                break
            move_name = ans_list[i].split(" ")[0]
            board_null = get_board_from_pos_cmd(start_pos + " " + pv + " " + info.pv[0])
            # 王手の場合はこの処理は出来ない
            if board_null.is_check():
                null_enemy_move_info.append(None)
                null_enemy_sfen_list.append([])
                null_enemy_value_list.append(-99999)
                null_enemy_ans_list.append("王手")
                continue
            else:
                null_sfen_enemy, null_info_enemy = get_nullmove_info(
                    engine, start_pos + " " + pv + " " + info.pv[0], go_cmd_null_enemy
                )
                temp_ans_list, temp_sfen_list, temp_value_list = parse_pv_info(
                    null_sfen_enemy, null_info_enemy, move_name
                )
                # multipv入りで読んでいたとしてもidx0しか使わない。情報が多すぎて邪魔になるから
                # TODO この瞬間だけmultipvを1に切り替えたい.....が、やねうら以外のサポートを考えるとだるすぎるので諦めよう
                null_enemy_move_info.append(null_info_enemy)
                null_enemy_ans_list.append(temp_ans_list[0])
                null_enemy_value_list.append(temp_value_list[0])
                null_enemy_sfen_list.append(temp_sfen_list[0])

    return NextPlyQuestion(
        question_pos=start_pos + " " + pv,
        question_sfen=board.sfen(),
        playinfo=infos,
        before_pos=start_pos,
        before_pv=pv,
        selection_usi=selection_usi,
        values=value_list,
        selection_ja=None,
        pv_value_ja=ans_list,
        go_cmd_ans=go_cmd,
        go_cmd_calc=go_cmd_calc,
        play_info_calc=info_calc,
        pv_sfen=sfen_list,
        null_move_info=null_info,
        null_ans_list=null_ans_list,
        null_sfen_list=null_sfen_list,
        null_value_list=null_value_list,
        null_enemy_move_info=null_enemy_move_info,
        null_enemy_ans_list=null_enemy_ans_list,
        null_enemy_sfen_list=null_enemy_sfen_list,
        null_enemy_value_list=null_enemy_value_list,
    )

    ques_ja = []
    ans_ja = []
    ques_usi = []
    values = []
    for info in infos.infos:
        mv_str = translate_pv(start_pos + " " + pv, [info.pv[0]])
        ques_ja.append(mv_str)
        values.append(info.eval)
        ques_usi.append(info.pv[0])
        ans = f"{mv_str} 評価値 {info.eval} : "
        ans += translate_pv(start_pos + " " + pv, info.pv)
        ans_ja.append(ans)

    board = get_board_from_pos_cmd(start_pos + " " + pv)
    return NextPlyQuestion(
        question_pos=start_pos + " " + pv,
        question_sfen=board.sfen(),
        playinfo=infos,
        before_pos=start_pos,
        before_pv=pv,
        selection_usi=ques_usi,
        values=values,
        selection_ja=ques_ja,
        pv_value_ja=ans_ja,
        go_cmd_ans=go_cmd,
        go_cmd_calc=go_cmd_calc,
        play_info_calc=info_calc,
    )
