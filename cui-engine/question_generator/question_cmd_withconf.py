import argparse
import dataclasses
import glob
import json
import os
from typing import List

import yaml
from dacite import Config, from_dict
from sekisyu.engine.config_engine import ConfigEngine
from sekisyu.engine.engine_generator import generate_engine
from sekisyu.qgen.question_generator import generate_question_from_pos
from shogi import CSA, KIF, Board


def run_sfen(sfen_to_use, config, engine, output):
    ques = generate_question_from_pos(
        f"position sfen {sfen_to_use} moves",
        engine,
        config["go_cmd"],
        1,
        0,
        0,
        go_cmd_calc=config["go_cmd_calc"] if "go_cmd_calc" in config else None,
        go_cmd_null=config["go_cmd_null"] if "go_cmd_null" in config else None,
        go_cmd_null_enemy=config["go_cmd_null_enemy"]
        if "go_cmd_null_enemy" in config
        else None,
    )

    with open(output, "w", encoding="utf8") as f:
        json.dump(
            dataclasses.asdict(ques),
            f,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
            separators=(",", ": "),
        )


def run_kif(file_names: List[str], config, engine, output_root) -> None:
    """
    棋譜ファイルを受け取って纏めて解析するコマンドも付ける(qsaから解析＋可視化をしたい)
    """

    for file_name in file_names:
        print("parse", file_name)
        if file_name.endswith(".kif"):
            data = KIF.Parser.parse_file(file_name)[0]
        elif file_name.endswith(".csa"):
            data = CSA.Parser.parse_file(file_name)[0]
        else:
            raise ValueError
        save_dir = f"{output_root}/data_{os.path.basename(file_name)}"
        os.makedirs(save_dir, exist_ok=True)
        board = Board(data["sfen"])
        for i, move in enumerate(data["moves"]):
            ques = generate_question_from_pos(
                f"position sfen {board.sfen()} moves",
                engine,
                config["go_cmd"],
                1,
                0,
                0,
                go_cmd_calc=config["go_cmd_calc"] if "go_cmd_calc" in config else None,
                go_cmd_null=config["go_cmd_null"] if "go_cmd_null" in config else None,
                go_cmd_null_enemy=config["go_cmd_null_enemy"]
                if "go_cmd_null_enemy" in config
                else None,
            )
            output_file_name = f"{save_dir}/{i:03}_{board.sfen().replace('/' ,'_').replace(' ', '_')}.json"
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


def main():
    """
    外部から問題生成ルーチンを呼ぶためのもの。逐一エンジンをブートするから遅い。
    electronからpipeができれば問題解決だが実際どうなんだ→windowsじゃ出来ない様子。これだから窓は
    """
    parser = argparse.ArgumentParser(description="set files to analyze")
    parser.add_argument("--sfen", default=None)
    parser.add_argument("--kif", default=None)
    parser.add_argument("--kif_out_root", default="kif_output")
    parser.add_argument("--config", default="question_cmd_config.yaml")
    parser.add_argument("--output", default="question_gen.json")

    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    engine_config: ConfigEngine() = from_dict(
        data_class=ConfigEngine,
        data=config["engine_config"],
        config=Config(cast=[tuple, int, str]),
    )
    engine = generate_engine(engine_config)

    # あまり上品なコードではないがバイナリを増やしたくない
    if args.sfen is not None:
        sfen_to_use = args.sfen.replace("__space__", " ")
        run_sfen(sfen_to_use, config, engine, args.output)
    if args.kif is not None:
        # ワイルドカード対応
        kif_list = glob.glob(args.kif)
        run_kif(kif_list, config, engine, args.kif_out_root)
    engine.quit()


if __name__ == "__main__":
    main()
