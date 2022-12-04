import argparse
import dataclasses

from sekisyu.engine.config_engine import ConfigEngine
from sekisyu.engine.engine_generator import generate_engine
from sekisyu.qgen.question_generator import generate_question_from_pos


def main():
    """
    外部から問題生成ルーチンを呼ぶためのもの。逐一エンジンをブートするから遅い。
    electronからpipeができれば問題解決だが実際どうなんだ
    """
    parser = argparse.ArgumentParser(description="set files to analyze")
    parser.add_argument("--sfen", required=True)
    parser.add_argument("--engine_path", type=str, required=True)
    parser.add_argument("--engine_name", type=str, default="engine")
    parser.add_argument("--engine_mode", type=str, default="yaneuraou")
    parser.add_argument("--multipv", type=int, default=10)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--evaldir", type=str, default="eval")
    parser.add_argument("--nodes", type=str, default="100000")  # intだと不安。本当？

    args = parser.parse_args()
    engine = generate_engine(
        ConfigEngine(
            engine_name=args.engine_name,
            engine_path=args.engine_path,
            option=[
                ("Threads", str(args.threads)),
                ("EvalDir", args.evaldir),
                ("MultiPV", str(args.multipv)),
            ],
        )
    )

    sfen_to_use = args.sfen.replace("__space__", " ")
    ques = generate_question_from_pos(
        f"position sfen {sfen_to_use}",
        engine,
        f"go nodes {args.nodes}",
        1,
        0,
        0,
        "go nodes 10000",
        f"go nodes {args.nodes}",
        f"go nodes {args.nodes}",
    )

    # json形式のテキストを返せば良い。subprocessから回収するとなると一行にしたほうが多分良い
    # 此奴がwindows(nuitka+windows?)かんきょうだとまともにうごかない
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(dataclasses.asdict(ques))
    engine.quit()
    # raise ValueError


if __name__ == "__main__":
    main()
