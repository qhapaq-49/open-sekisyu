import time

from sekisyu.engine.base_engine import BaseEngine, Turn, UsiEngineState


class DlshogiEngine(BaseEngine):
    """
    dlshogiのクラス

    USIプロトコルを介し、対局や各種局面の解析を行う。
    特定のエンジンにしか無い機能はここに適宜書いていく

    1. dlshogiではmultipvのnodesを各手別の訪問数に書き換えるための処置を入れる
    2. dlshogiはusiプロトコルのponderに頼らない作りになっているがアンサンブルなどを取るときに
    インターフェイスが統一されてないと不便なのでメッセージを無視する形で対応する
    """

    def __init__(self, engine_name: str = "") -> None:
        super().__init__(engine_name)
        self.ponder_str = None
        # TODO : このへんもうちょっとマトモな実装があると思う
        self.print_info_before = None

    def reflesh_game(self) -> None:
        self.send_command("isready")  # 先行して"isready"を送信
        self.change_state(UsiEngineState.WaitReadyOk)

    # エンジンとやりとりを行うスレッド(write方向)
    def write_worker(self):

        for option in self.options:
            self.send_command(
                "setoption name {0} value {1}".format(option[0], option[1])
            )
        self.send_command("isready")  # 先行して"isready"を送信
        self.change_state(UsiEngineState.WaitReadyOk)
        self.ponder_str = None

        try:
            while True:
                message = self.send_queue.get()
                # 先頭の文字列で判別する。
                messages = message.split()
                if len(messages):
                    token = messages[0]
                else:
                    token = ""
                # stopコマンドではあるが、goコマンドを送信していないなら送信しない。
                if token == "stop":
                    # stopをもらったらresignを吐く
                    # looks like dlshogi does not return bestmove
                    # make move to legal thanks to shameful usi protocol
                    # self.think_result.infos[0].pv[0] = "resign"
                    self.change_state(UsiEngineState.WaitCommand)
                elif token == "go":
                    # go ponderは無視する
                    if self.print_info_before is None:
                        self.print_info_before = self.print_info
                    self.set_print_info(self.print_info_before)
                    if messages[1] == "ponder":
                        print(
                            "info string dlshogi engine does not depends on shameful usi ponder protocol"
                        )
                        self.ponder_str = message.replace("ponder", "")
                        self.change_state(UsiEngineState.WaitBestmove)
                        continue
                    else:
                        self.ponder_str = None
                    # go cmdならthink_resultを初期化する
                    self.think_result.infos = []
                    self.wait_for_state(UsiEngineState.WaitCommand)
                    self.change_state(UsiEngineState.WaitBestmove)
                # positionコマンドは、WaitCommand状態でないと送信できない。
                elif token == "position":
                    self.position = message
                    self.wait_for_state(UsiEngineState.WaitCommand)
                elif token == "moves" or token == "side":
                    self.wait_for_state(UsiEngineState.WaitCommand)
                    self.change_state(UsiEngineState.WaitOneLine)
                elif token == "usinewgame" or token == "gameover":
                    self.reflesh_game()

                    self.wait_for_state(UsiEngineState.WaitCommand)
                elif token == "ponderhit":
                    # ponderhitも破棄する
                    if self.ponder_str is not None:
                        print(f"info string ponderhit go_cmd {self.ponder_str}")
                        self.send_command(self.ponder_str)
                        continue
                self.proc.stdin.write(message + "\n")
                self.proc.stdin.flush()

                if token == "quit":
                    self.change_state(UsiEngineState.Disconnected)
                    # 終了コマンドを送信したなら自発的にこのスレッドを終了させる。
                    break

                retcode = self.proc.poll()
                if retcode is not None:
                    break

        except Exception:
            raise ValueError

    # エンジン側から送られてきたメッセージを解釈する。
    def dispatch_message(self, message: str):
        # 最後に受信した文字列はここに積む約束になっている。
        self.last_received_line = message

        # 先頭の文字列で判別する。
        index = message.find(" ")
        if index == -1:
            token = message
        else:
            token = message[0:index]

        # --- handleするメッセージ

        # 1行待ちであったなら、これでハンドルしたことにして返る。
        if self.engine_state == UsiEngineState.WaitOneLine:
            self.change_state(UsiEngineState.WaitCommand)
            return
        # "isready"に対する応答
        elif token == "readyok":
            # print("info string receive readyok from engine", flush=True)
            self.change_state(UsiEngineState.WaitCommand)
        # "go"に対する応答
        elif token == "bestmove":
            # 指し手待機の状態になるまで待機
            time.sleep(0.001)
            self.handle_bestmove(message)
            # print("bm received")
            self.think_result.generate_ponder_from_pv()
            self.change_state(UsiEngineState.WaitCommand)
            self.print_info_before = self.print_info
            self.set_print_info(False)
        # エンジンの読み筋に対する応答
        elif token == "info":
            if self.print_info:
                # 将棋所のUIがイミフなのでテキスト表示回りがバグるのはもう諦める
                print(message, flush=True)
            self.handle_info(message)
        elif "move_count" in message:
            # 候補手の生成順序の順番で出てくる。
            mpv_ply = message.split(" ")[0].split(":")[-1]
            mpv_nodes = int(message.split("move_count:")[1].split(" ")[0])
            for idx in range(len(self.think_result.infos)):
                if self.think_result.infos[idx].pv[0] == mpv_ply:
                    self.think_result.infos[idx].nodes = mpv_nodes

        elif self.engine_state == UsiEngineState.PrintUSI:
            if token == "usiok":
                self.change_state(UsiEngineState.WaitCommand)
            elif not token.startswith("id"):
                self.usi_options.append(message)
