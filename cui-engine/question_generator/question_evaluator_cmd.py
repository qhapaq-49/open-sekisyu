import argparse
import dataclasses
import glob
import json
import os

import yaml
from dacite import Config, from_dict
from sekisyu.engine.config_engine import ConfigEngine
from sekisyu.engine.engine_generator import generate_engine
from sekisyu.qgen.next_ply_question import NextPlyQuestion
from sekisyu.qgen.question_evaluator import Difficulty
from sekisyu.qgen.question_generator import generate_question_from_pos
from tqdm import tqdm


def main():
    """
    問題の難易度を測定してjsonに上書きする
    """
    parser = argparse.ArgumentParser(description="set files to analyze")
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", default="")
    parser.add_argument("--force_analyze", action="store_true")
    parser.add_argument("--force_update", action="store_true")
    parser.add_argument("--force_calc", action="store_true")
    args = parser.parse_args()
    file_list = glob.glob(args.file)

    if args.force_analyze or args.force_calc:
        assert args.config != ""
        assert os.path.exists(args.config)

    if args.config != "":
        with open(args.config) as f:
            config = yaml.safe_load(f)
        engine_config: ConfigEngine() = from_dict(
            data_class=ConfigEngine,
            data=config["engine_config"],
            config=Config(cast=[tuple, int, str]),
        )
        engine = generate_engine(engine_config)
        print("engine boot done")
    else:
        engine = None

    for file_name in tqdm(file_list):
        with open(file_name) as f:
            data = json.load(f)
        ques = from_dict(
            data_class=NextPlyQuestion, data=data, config=Config(cast=[tuple, int, str])
        )
        if not args.force_update and ques.difficulty:
            continue
        print(file_name)
        # データに不足がある場合、configが与えられていれば追加で計算する
        # TODO : version比較
        if args.force_analyze:
            # ここを常に最新版にすることで最低限の互換性を用意できる
            # TODO : データの再計算をしない、単純なupdaterも必要かも
            ques = generate_question_from_pos(
                f"position sfen {ques.question_sfen} moves",
                engine,
                config["go_cmd"],
                1,
                0,
                0,
                go_cmd_calc=config["go_cmd_calc"],
                go_cmd_null=config["go_cmd_null"],
                go_cmd_null_enemy=config["go_cmd_null_enemy"]
                if "go_cmd_null_enemy" in config
                else None,
            )
        elif args.force_calc or ques.play_info_calc is None:
            # calcは難易度評価に必ず必要なのでチェックする
            engine.send_command(f"position sfen {ques.question_sfen} moves")
            info_calc = engine.send_go_and_wait(config["go_cmd_calc"])
            ques.play_info_calc = info_calc
            ques.go_cmd_calc = config["go_cmd_calc"]

        # 問題の難易度を測定する
        # パスした時の評価値と適切な手を指した時の評価値の違いを手の重要度とする
        # 浅い読みの評価と正解の手の評価の違いを難易度とする
        is_check = False
        if ques.null_value_list:
            diff = ques.null_value_list[0] + ques.values[0]
        else:
            # 王手局面
            if len(ques.playinfo.infos) > 1:
                diff = ques.playinfo.infos[0].eval - ques.playinfo.infos[1].eval
            else:
                diff = 0
            is_check = True

        # 問題の難易度を測定
        ply_calc = ques.play_info_calc.infos[0].pv[0]
        value_orig = ques.playinfo.infos[0].eval
        value_diff = 0
        for info in ques.playinfo.infos:
            value_diff = value_orig - info.eval
            if info.pv[0] == ply_calc:
                break

        ques.difficulty = Difficulty(
            version="1.0.0",
            null_diff=diff,
            value_diff=value_diff,
            is_check=is_check,
            infos={},
        )

        # difficultyを上書きする
        with open(file_name, "w", encoding="utf8") as f:
            json.dump(
                dataclasses.asdict(ques),
                f,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
                separators=(",", ": "),
            )
    if engine:
        engine.quit()


if __name__ == "__main__":
    main()
