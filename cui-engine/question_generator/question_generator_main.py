import argparse
import dataclasses

# from sekisyu.qgen.question_render import ConfigQuestionRender, question_render
import glob
import json
import os
from typing import List, Optional

import yaml
from dacite import Config, from_dict
from sekisyu.board.get_board_from_pos_cmd import get_board_from_pos_cmd
from sekisyu.engine.config_engine import ConfigEngine
from sekisyu.engine.engine_generator import generate_engine

# from sekisyu.board.board_to_png_l2 import ConfigBoard
from sekisyu.qgen.question_generator import generate_question_from_pos
from shogi import CSA, KIF, Board


@dataclasses.dataclass
class ConfigQuestionGenerator:
    kifs: List[str]
    engine_config: ConfigEngine
    # config_render : ConfigQuestionRender
    loop_per_kif: int = 1
    hero: Optional[str] = None
    move_min_kif: int = 4
    move_max_kif: int = 20
    move_max_ques: int = 1
    output_dir: str = "ques_output"
    # hero enemy側の探索時のノイズ
    noise_hero: int = 0
    noise_enemy: int = 666
    # hero側の評価値のレンジ
    hero_eval_min: int = -9999
    hero_eval_max: int = 9999
    # 上位2つの評価値の差（この一手度合い）
    diff_min: int = -300

    go_cmd: str = "go nodes 500000"


def modify_config(config: ConfigQuestionGenerator):
    while True:
        kif_path = input("kifpath : 解析する棋譜の場所を指定してください（デフォルト:kif）")
        if kif_path == "":
            kif_path = "kif"
        kifnum = len(glob.glob(kif_path + "/*kif")) + len(glob.glob(kif_path + "/*csa"))
        if kifnum == 0:
            print("棋譜が見つかりません", kif_path)
            continue
        print(kifnum, "局の棋譜を見つけました")
        break

    config.kifs = [kif_path + "/*.csa", kif_path + "/*.kif"]

    output_dir = "output"
    txt_in = input("output_dir : 問題を出力するフォルダ名（デフォルト：output）")
    if txt_in != "":
        output_dir = txt_in

    config.output_dir = output_dir

    while True:
        hero = input("hero : 先手/後手のどちらの局面を問題にしますか？（先手：b、後手：w、両方：-（デフォルト：-））")
        if hero == "" or hero == "-":
            config.hero = None
        elif hero == "b":
            config.hero = "black"
        elif hero == "w":
            config.hero = "white"
        else:
            print("不正なインプット", hero)
            continue
        break

    while True:
        # node数はintに収まらない可能性があるので一応strにしとく
        node = 500000
        nodes = input("nodes : 解析に用いるノード数(go nodes)を指定してください（デフォルト：500000）")
        if nodes != "":
            try:
                nodes = int(node)
            except ValueError:
                print("不正なインプット", nodes)
                continue
        else:
            nodes = "500000"
        break
    config.go_cmd = f"go nodes {nodes}"

    while True:
        threads = 4
        txt_in = input("threads : 探索時に使うスレッド数を指定してください（デフォルト4）")
        if txt_in != "":
            try:
                threads = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break

    config.engine_config.option.append(["Threads", str(threads)])

    while True:
        multipv = 10
        mpv = input("multipv : 解析で出力する手の数(MultiPV)を指定してください（デフォルト：10）")
        if mpv != "":
            try:
                multipv = int(mpv)
                break
            except ValueError:
                print("不正なインプット", mpv)
                continue
        break
    config.engine_config.option.append(["MultiPV", f"{multipv}"])

    while True:
        move_min = 4
        txt_in = input("move_min : 解析に用いる局面の最小手数を指定してください（デフォルト：4）")
        if txt_in != "":
            try:
                move_min = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break
    config.move_min_kif = move_min

    while True:
        move_max = 100
        txt_in = input("move_max : 解析に用いる局面の最大手数を指定してください（デフォルト：100）")
        if txt_in != "":
            try:
                move_max = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break
    config.move_max_kif = move_max

    while True:
        move_max_q = 1
        txt_in = input("random_move_max : ランダムムーブの最大手数を指定してください（デフォルト1）")
        if txt_in != "":
            try:
                move_max_q = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break
    config.move_max_ques = move_max_q

    while True:
        noise_hero = 0
        txt_in = input("noise_hero : ランダムムーブ時の自分の手のノイズの大きさを指定してください（デフォルト0）")
        if txt_in != "":
            try:
                noise_hero = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break
    config.noise_hero = noise_hero

    while True:
        noise_enemy = 600
        txt_in = input("noise_enemy : ランダムムーブ時の相手の手のノイズの大きさを指定してください（デフォルト600）")
        if txt_in != "":
            try:
                noise_enemy = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break
    config.noise_enemy = noise_enemy

    while True:
        loop_num = 1
        txt_in = input("noise_loop : ランダムムーブによる局面生成を各対局ごとに何回行うか（デフォルト1）")
        if txt_in != "":
            try:
                loop_num = int(txt_in)
                break
            except ValueError:
                print("不正なインプット", txt_in)
                continue
        break
    config.loop_per_kif = loop_num


def main():
    """
    sample question_generator_main.py --config question_generator_example.yaml
    """
    parser = argparse.ArgumentParser(description="set files to analyze")
    parser.add_argument(
        "--config", default="config.yaml", help="config files for analysis"
    )
    parser.add_argument("--no_conf", action="store_true")
    args = parser.parse_args()
    with open(args.config) as f:
        conf_dict = yaml.safe_load(f)

    config_qgen: ConfigQuestionGenerator = from_dict(
        data_class=ConfigQuestionGenerator,
        data=conf_dict["ques_config"],
        config=Config(cast=[tuple, int, str]),
    )

    if not args.no_conf:
        modify_config(config_qgen)

    try:
        engine = generate_engine(config_qgen.engine_config)
        print("棋譜解析用のエンジン起動 ...... OK")
        print("debug message : ", config_qgen.engine_config)
    except Exception:
        print("棋譜解析用のエンジンの起動に失敗しました")
        print("debug message : ", config_qgen.engine_config)
        raise ValueError
    kifs = []
    for kif in config_qgen.kifs:
        kifs.extend(glob.glob(kif))

    os.makedirs(config_qgen.output_dir, exist_ok=True)

    for kif in kifs:
        ques_dict = {}
        if kif.endswith(".kif"):
            data = KIF.Parser.parse_file(kif)[0]
        elif kif.endswith(".csa"):
            data = CSA.Parser.parse_file(kif)[0]
        else:
            raise ValueError

        for move_use in range(config_qgen.move_max_ques + 1):
            save_dir = (
                f"{config_qgen.output_dir}/{os.path.basename(kif)}/change{move_use}"
            )
            os.makedirs(save_dir, exist_ok=True)
            loop_per_kif = config_qgen.loop_per_kif if move_use > 0 else 1
            for loop in range(loop_per_kif):
                pos_cmd = "position startpos moves "
                board = Board()
                for i, move in enumerate(data["moves"]):

                    # 対局が終了、手数オーバーは即座に終了
                    if move == "resign":
                        print("battle finish")
                        break

                    if i > config_qgen.move_max_kif:
                        break

                    is_skip = False

                    # 手数追加なしの場合、その局面の解析をするだけ
                    if move_use == 0:
                        if config_qgen.hero == "black" and i % 2 == 1:
                            is_skip = True
                        if config_qgen.hero == "white" and i % 2 == 0:
                            is_skip = True
                    else:
                        # 手数追加ありの場合、初期局面は相手の手番（先手を解析するなら後手の局面がスタート）
                        if config_qgen.hero == "black" and i % 2 == 0:
                            is_skip = True
                        if config_qgen.hero == "white" and i % 2 == 1:
                            is_skip = True

                    # 手数があってないなら飛ばす
                    if i < config_qgen.move_min_kif:
                        is_skip = True

                    if is_skip:
                        board.push_usi(move)
                        pos_cmd += move + " "
                        continue

                    if move_use == 0:
                        ques = generate_question_from_pos(
                            pos_cmd,
                            engine,
                            config_qgen.go_cmd,
                            1,
                            config_qgen.noise_hero,
                            config_qgen.noise_enemy,
                            "go nodes 2020",
                            config_qgen.go_cmd,
                            config_qgen.go_cmd,
                            2,
                        )
                    else:
                        ques = generate_question_from_pos(
                            pos_cmd,
                            engine,
                            config_qgen.go_cmd,
                            move_use * 2,
                            config_qgen.noise_enemy,
                            config_qgen.noise_hero,
                            "go nodes 2020",
                            config_qgen.go_cmd,
                            config_qgen.go_cmd,
                            2,
                        )
                    if ques is None:
                        board.push_usi(move)
                        pos_cmd += move + " "
                        continue
                    if ques.question_pos not in ques_dict:
                        ques_dict[ques.question_pos] = ques
                        board_sfen = (
                            get_board_from_pos_cmd(ques.question_pos)
                            .sfen()
                            .replace("/", "_")
                            .replace(" ", "_")
                        )
                        output_file_name = f"{save_dir}/{i:03}_{board_sfen}.json"
                        # question_render(ques, config_qgen.config_render, output_file_name.replace(".json", ".png"))
                        # ques.ques_path = f"{i}_{board_sfen}.png"
                        with open(output_file_name, "w", encoding="utf8") as f:
                            json.dump(
                                dataclasses.asdict(ques),
                                f,
                                ensure_ascii=False,
                                indent=4,
                                sort_keys=True,
                                separators=(",", ": "),
                            )
                    board.push_usi(move)
                    pos_cmd += move + " "

        print("finish", kif)
    engine.quit()


if __name__ == "__main__":
    main()
