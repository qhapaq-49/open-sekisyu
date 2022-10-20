import glob
import json
from typing import Dict, List, Optional

from sekisyu.kif_analyzer.accuracy_pack import AccuracyPack, ConfigAccuracyPack
from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.playout.playout import BasePlayOut
from sekisyu.title_parse.title_parse import search_filter
from tqdm import tqdm


def get_ply_rank(ply: BasePlayInfoPack, ply_str) -> int:
    for i, info in enumerate(ply.infos):
        if ply_str == info.pv[0]:
            return i
    return -1


def add_value(
    apack: AccuracyPack,
    playout: BasePlayOut,
    is_black: bool,
    ply_max: int,
    ply_range: int,
    eval_min: int,
    eval_max: int,
    eval_range: int,
    sudden_death_value: int = 600,
) -> None:
    """
    playoutからaccuracy packを更新する

    apack (AccuracyPack) : 更新されるAccuracyPack
    playout (BasePlayOut) : このプレイアウトを足し合わせる
    is_black(bool) : 先手番か否かのスイッチ
    """

    apack.kif_count += 1

    for i, ev in enumerate(playout.evalinfo_list):
        is_player = False
        if i % 2 == 0 and is_black:
            is_player = True
        if i % 2 == 1 and not is_black:
            is_player = True
        if i >= len(playout.plys):
            break

        current_eval = ev.infos[0].eval
        next_ev = (
            ev.infos[0].eval
            if i + 1 >= len(playout.evalinfo_list)
            else -playout.evalinfo_list[i + 1].infos[0].eval
        )
        # multipvでみて順位がいくらか
        ply_rank = get_ply_rank(ev, playout.plys[i])
        ply_id = min(ply_max // ply_range, i // ply_range)
        eval_id = 1 + (current_eval - eval_min) // eval_range
        if current_eval < eval_min:
            eval_id = 0
        if eval_id > (eval_max - eval_min) // eval_range:
            eval_id = (eval_max - eval_min) // eval_range + 1

        if is_player:
            apack.rank_count[ply_rank][ply_id] += 1
            apack.rank_count_eval[ply_rank][eval_id] += 1
            # 詰みの見逃しのカウント
            if current_eval > 30000:
                if next_ev < 30000:
                    apack.miss_mate_count += 1
                apack.ply_mate_sum += 1

            # 有利な局面から頓死した数 + 詰みがあった局面から不利にした数
            # = 詰め将棋が出来たら勝てたはずの局面数
            if current_eval > sudden_death_value:
                if next_ev < -30000:
                    apack.sudden_death_count += 1
                apack.ply_sudden_death += 1

            if current_eval > 30000:
                if next_ev < -sudden_death_value:
                    apack.sudden_death_count += 1
                apack.ply_sudden_death += 1

        # TODO opponentをどうする


def get_accuracy_with_filter(
    json_dirs: List[str],
    filter_names: List[str],
    config: ConfigAccuracyPack,
    write_out_of_filter: bool = False,
    name_out_of_filter: str = "",
    auto_filter: bool = False,
    use_timestamp: Optional[int] = None,
) -> Dict[str, AccuracyPack]:
    """
    playoutのjsonファイルを受け取って手の一致率を返す。
    jsonファイルから対局者の名前を取り出してフィルタをかけることで、
    雑多なファイル群からプレイヤー別のaccuracy_packを返す

    json_dirs (list(str)): jsonが格納されたフォルダのリスト。
    filter_names (list(str)) : プレイヤー名として検索する名前のリスト。正規表現可 TODO:Noneにした場合は全部抜き出す？
    config (ConfigAccuracyPack) : 一致率解析の条件
    write_out_of_filter (bool) : filterに引っかからなかったデータについて出力をするか
    name_out_of_filter (str) : filterに引っかからなかったデータにつける名前。write_out_of_filterがTrueでなければ使われない
    use_timestamp(int) : noneじゃない場合、この文字数分だけtimesampを取ってタグにする

    return:
        AccuracyPack : 手の一致率のデータセットのdict。keyはプレイヤー名
    """
    json_list = []
    for json_dir in json_dirs:
        json_list.extend(glob.glob(json_dir + "/*.json"))

    ap_dict = {}

    for json_name in tqdm(json_list):
        with open(json_name) as f:
            try:
                dat = json.load(f)
            except json.decoder.JSONDecodeError:
                print(f"bad json file {json_name}")
                continue
        playout: BasePlayOut = BasePlayOut.from_dict(dat)

        # 先手番のプレイヤー名を検索
        pl_name = playout.player_name[0]
        if use_timestamp:
            pl_name += (
                "_" + playout.timestamp[: min(len(playout.timestamp), use_timestamp)]
            )
        idx_black = search_filter(pl_name, filter_names, auto_filter)
        name_to_append = (
            filter_names[idx_black]
            if idx_black is not None
            else name_out_of_filter
            if write_out_of_filter
            else None
        )
        if name_to_append is not None:
            if name_to_append not in ap_dict:
                ap_dict[name_to_append] = AccuracyPack(config=config)
                ap_dict[name_to_append].load_config(config)
            add_value(
                ap_dict[name_to_append],
                playout,
                True,
                config.ply_max,
                config.ply_range,
                config.eval_min,
                config.eval_max,
                config.eval_range,
            )

        # 後手番のプレイヤー名を検索
        pl_name = playout.player_name[1]
        if use_timestamp:
            pl_name += (
                "_" + playout.timestamp[: min(len(playout.timestamp), use_timestamp)]
            )

        idx_white = search_filter(pl_name, filter_names, auto_filter)
        name_to_append = (
            filter_names[idx_white]
            if idx_white is not None
            else name_out_of_filter
            if write_out_of_filter
            else None
        )
        if name_to_append is not None:
            if name_to_append not in ap_dict:
                ap_dict[name_to_append] = AccuracyPack(config=config)
                ap_dict[name_to_append].load_config(config)
            add_value(
                ap_dict[name_to_append],
                playout,
                False,
                config.ply_max,
                config.ply_range,
                config.eval_min,
                config.eval_max,
                config.eval_range,
            )

    for key in ap_dict:
        ap_dict[key].calc_prod()

    return ap_dict


def get_accuracy(root_json_dir: str, config: ConfigAccuracyPack) -> AccuracyPack:
    """
    棋譜解析のjsonファイルを受け取って手の一致率を返す。
    dataframeを使いたいのだがpandasを入れると
    バイナリのサイズがデカくなるので泣く泣くpandas使わない縛り

    root_json_dir (str): jsonが入っているフォルダ。blackとwhite以下にjsonがあることが前提
    config (ConfigAccuracyPack) : 一致率解析の条件

    return:
        AccuracyPack : 手の一致率のデータセット
    """
    black_json_list = glob.glob(root_json_dir + "/black/*.json")
    white_json_list = glob.glob(root_json_dir + "/white/*.json")
    apack = AccuracyPack(config=config)
    apack.load_config(config)

    for black_json in tqdm(black_json_list):
        with open(black_json) as f:
            try:
                dat = json.load(f)
            except json.decoder.JSONDecodeError:
                print(f"bad json file {black_json}")
                continue
        playout = BasePlayOut.from_dict(dat)
        add_value(
            apack,
            playout,
            True,
            config.ply_max,
            config.ply_range,
            config.eval_min,
            config.eval_max,
            config.eval_range,
        )

    for white_json in tqdm(white_json_list):
        with open(white_json) as f:
            try:
                dat = json.load(f)
            except json.decoder.JSONDecodeError:
                print(f"bad json file {white_json}")
                continue
        playout = BasePlayOut.from_dict(dat)
        add_value(
            apack,
            playout,
            False,
            config.ply_max,
            config.ply_range,
            config.eval_min,
            config.eval_max,
            config.eval_range,
        )

    apack.calc_prod()
    return apack
