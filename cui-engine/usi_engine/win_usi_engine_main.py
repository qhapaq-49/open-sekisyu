import argparse
import sys
import threading
from queue import Queue

import yaml
from sekisyu.engine.base_engine import BaseEngine, UsiEngineState
from sekisyu.engine.engine_generator import generate_engine_dict

# TODO : どういうわけかログの出力が尋常じゃなく遅い
# nuitkaのバージョンを上げたら解決した。フリーランチバンザイ...?


def add_input(input_queue):
    while True:
        txt = sys.stdin.readline().rstrip()
        if txt != "":
            input_queue.put(txt)


def usi_engine(engine: BaseEngine):
    """
    engineを各種guiに接続する
    engine (BaseEngine) : 使うエンジン
    """
    # 現在bestmoveを待機中である
    wait_bestmove: bool = False

    engine.set_print_info(True)
    input_queue = Queue()

    # 標準入力をマルチスレッドで入れる
    # https://stackoverflow.com/questions/2408560/non-blocking-console-input
    input_thread = threading.Thread(target=add_input, args=(input_queue,))
    input_thread.daemon = True
    input_thread.start()

    while True:
        if not input_queue.empty():
            message = input_queue.get()
            # 先頭の文字列で判別する。
            messages = message.split()
            if len(messages):
                token = messages[0]
            if token == "go":
                engine.send_command(message)
                engine.wait_for_state(UsiEngineState.WaitBestmove)
                wait_bestmove = True
            elif token == "isready":
                # エンジンはboot済であることを仮定
                engine.send_isready_and_wait()
                print("readyok", flush=True)
            elif token == "usi":
                options = engine.get_usi_option()
                print("id name " + engine.get_name())
                for option in options:
                    print(option, flush=True)
                print("usiok", flush=True)
            elif token == "setoption":
                engine.send_command(message)
            elif token == "quit":
                engine.quit()
                break
            else:
                engine.send_command(message)
        else:
            # 標準入力がないときはエンジンからの出力を待つ
            # もとい、bestmoveを受け取ったらそれをパースして出力する
            if wait_bestmove:
                if engine.get_state() == UsiEngineState.WaitCommand:
                    ply = engine.get_current_think_result()
                    ply = engine.parse_pv(ply)
                    print(
                        "bestmove " + ply.bestmove + " ponder " + ply.ponder, flush=True
                    )
                    wait_bestmove = False


def main():
    """
    config.yamlに書かれたエンジンを起動する
    """
    parser = argparse.ArgumentParser(description="set files to analyze")
    parser.add_argument(
        "--config", default="config.yaml", help="config files for analysis"
    )
    args = parser.parse_args()
    with open(args.config, "r") as f:
        conf_dict = yaml.safe_load(f)
    engine = generate_engine_dict(conf_dict)
    usi_engine(engine)


if __name__ == "__main__":
    main()
