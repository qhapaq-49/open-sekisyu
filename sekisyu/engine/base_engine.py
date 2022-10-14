import os
import subprocess
import threading
import time
from enum import Enum, IntEnum
from queue import Queue
from typing import List, Tuple

from sekisyu.playout.playinfo import (
    BasePlayInfo,
    BasePlayInfoPack,
    generate_playinfo_from_info,
)

"""
エンジンとの通信部分の多くはAyaneを参考にしています

https://github.com/yaneurao/Ayane
"""


class Turn(IntEnum):
    BLACK = 0  # 先手
    WHITE = 1  # 後手

    # 反転させた手番を返す
    def flip(self) -> int:  # Turn:
        return Turn(int(self) ^ 1)


# UsiEngineクラスのなかで用いるエンジンの状態を表現するenum
class UsiEngineState(Enum):
    WaitConnecting = 1  # 起動待ち
    Connected = 2  # 起動完了
    WaitReadyOk = 3  # "readyok"待ち
    WaitCommand = 4  # "position"コマンド等を送信できる状態になった
    WaitBestmove = 5  # "go"コマンドを送ったので"bestmove"が返ってくるのを待っている状態
    WaitOneLine = 6  # "moves"など1行応答を返すコマンドを送信したのでその1行が返ってくるのを待っている状態
    PrintUSI = 7  # usiオプションへの返しを待っている
    Disconnected = 999  # 終了した


class BaseEngine:
    """
    USIプロトコル対応エンジンのモック。

    USIプロトコルを介し、探索などの各種コマンドを実行する
    """

    # --- private static members ---

    # 静的メンバ変数とする。UsiEngineのインスタンスの数を記録する
    static_count = 0

    # ↑の変数を変更するときのlock object
    static_lock_object = threading.Lock()

    def __init__(self, engine_name: str = "") -> None:
        """
        エンジンの初期化
        """
        self.engine_name = engine_name
        self.engine_path = None
        self.engine_state = None
        self.options = []
        # infoから始まる文字列を標準出力する(gui用のdirty hack)
        self.print_info = False
        self.think_result: BasePlayInfoPack = BasePlayInfoPack()
        # private
        # エンジンのプロセスハンドル
        self.proc = None

        # エンジンとやりとりするスレッド
        self.read_thread = None
        self.write_thread = None

        # 最後にエンジン側から受信した1行
        self.last_received_line = None

        # エンジンにコマンドを送信するためのqueue(送信スレッドとのやりとりに用いる)
        self.send_queue = Queue()

        # print()を呼び出すときのlock object
        self.lock_object = threading.Lock()

        # engine_stateが変化したときのイベント用
        self.state_changed_cv = threading.Condition()
        # このクラスのインスタンスの識別用ID。
        # 念の為、lockしてから参照/インクリメントを行う。
        with BaseEngine.static_lock_object:
            self.instance_id = BaseEngine.static_count
            BaseEngine.static_count += 1
        self.position = ""
        self.dead = False

    def get_name(self) -> str:
        """
        エンジン名を取得する

        Returns:
            str: エンジン名
        """
        if self.engine_name == "":
            return self.engine_path
        return self.engine_name

    def get_usi_option(self) -> List[str]:
        """
        usiコマンドで出力するべきオプションを列挙する

        return:
            list(str) : 標準出力されるべきstrのリスト
        """
        self.wait_for_state(UsiEngineState.WaitCommand)
        self.change_state(UsiEngineState.PrintUSI)
        self.usi_options = []
        self.send_command("usi")
        self.wait_for_state(UsiEngineState.WaitCommand)
        return self.usi_options

    def boot(self, engine_path: str) -> None:
        """
        エンジンを起動する

        engine_path (str):
            起動するエンジンのパス
        """

        # 別のエンジンを起動しているかもしれないので落とす
        self.quit()
        self.engine_state = None
        self.exit_state = None

        self.engine_path = engine_path

        # write workerに対するコマンドqueue
        self.send_queue = Queue()

        # 最後にエンジン側から受信した行
        self.last_received_line = None
        self.change_state(UsiEngineState.WaitConnecting)

        # このフィルタリングは本当は危うい
        if "ssh " not in self.engine_path:
            # 実行ファイルの存在するフォルダ
            self.engine_fullpath = os.path.join(os.getcwd(), self.engine_path)
            # subprocess.Popen()では接続失敗を確認する手段がないくさいので、
            # 事前に実行ファイルが存在するかを調べる。
            if not os.path.exists(self.engine_fullpath):
                self.change_state(UsiEngineState.Disconnected)
                self.exit_state = "Connection Error"
                raise FileNotFoundError(self.engine_fullpath + " not found.")
            
            self.proc = subprocess.Popen(
                self.engine_fullpath,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                encoding="shift-jis",
                cwd=os.path.dirname(self.engine_fullpath),
            )

        else:
            self.engine_fullpath = self.engine_path
            self.proc = subprocess.Popen(
                self.engine_fullpath,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                encoding="shift-jis",
            )        
        # self.send_command("usi")
        self.change_state(UsiEngineState.Connected)

        # 読み書きスレッド
        self.read_thread = threading.Thread(target=self.read_worker)
        self.read_thread.start()
        self.write_thread = threading.Thread(target=self.write_worker)
        self.write_thread.start()

    def change_multipv(self, multipv: int) -> None:
        """
        対局の途中でmultipvを変更する

        multipv (int) : 変更後のmultipv
        """
        self.send_command(f"setoption name MultiPV value {multipv}")

    # エンジンのconnect()が呼び出されたあとであるか
    def is_connected(self) -> bool:
        return self.proc is not None

    def quit(self) -> None:
        """
        エンジンにquitコマンドを送る
        """
        if self.proc is not None:
            self.send_command("quit")
            # スレッドをkillするのはpythonでは難しい。
            # エンジンが行儀よく動作することを期待するしかない。
            # "quit"メッセージを送信して、エンジン側に終了してもらうしかない。

        if self.read_thread is not None:
            self.read_thread.join()
            self.read_thread = None

        if self.write_thread is not None:
            self.write_thread.join()
            self.write_thread = None

        # GCが呼び出されたときに回収されるはずだが、UnitTestでresource leakの警告が出るのが許せないので
        # この時点でclose()を呼び出しておく。
        if self.proc is not None:
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.proc.stderr.close()
            self.proc.terminate()

        self.proc = None
        self.change_state(UsiEngineState.Disconnected)

    def set_print_info(self, print_info: bool) -> None:
        """
        エンジンのログ出力に関する設定を行う。
        Trueにすることでエンジンからの標準出力のうちinfoから始まるものが出力される

        print_info(bool):
            Trueにすることでエンジンからの標準出力のうちinfoから始まるものが出力される
        """
        self.print_info = print_info

    def set_option(self, options: List[Tuple[str, str]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """
        self.options = options

    def get_option(self) -> List[Tuple[str, str]]:
        """
        エンジンに送ったオプションを返す

        Returns:
            list((str, str)) : オプション一覧
        """
        return self.options

    def get_current_think_result(self) -> BasePlayInfoPack:
        """
        現時点でのpvの様子を吐く
        """
        return self.think_result

    def parse_pv(self, think_result: BasePlayInfoPack, is_ponder:bool=False) -> BasePlayInfoPack:
        """
        pvの後処理を行う。主にvirtual engineでmultipvの結果を処理して云々みたいな使い方をする
        デフォルトのbase_engineでは何もしない
        """
        return think_result

    def get_state(self):
        """
        現在のエンジンの状況を出力する
        """
        return self.engine_state

    def send_go_and_wait(self, go_cmd: str) -> BasePlayInfoPack:
        """
        エンジンにgo コマンドを送り、bestmoveが帰ってくるまで待つ。
        解析や自動対局を行う際に便利。排他的な処理であるためponder非対応であることに注意

        go_cmd (str):
            送られるgoコマンド。ex "go byoyomi 1000"
        """
        # 過去のgoの結果を消す
        self.think_result: BasePlayInfoPack = BasePlayInfoPack()
        self.send_queue.put(go_cmd)
        self.wait_for_state(UsiEngineState.WaitBestmove)
        self.wait_for_state(UsiEngineState.WaitCommand)
        return self.think_result

    def send_command(self, cmd: str) -> None:
        """
        エンジンに特別なコマンドを送る。
        """
        self.send_queue.put(cmd)

    # self.engine_stateを変更する。
    def change_state(self, state: UsiEngineState):
        # 切断されたあとでは変更できない
        if self.engine_state == UsiEngineState.Disconnected:
            return
        # goコマンドを送ってWaitBestmoveに変更する場合、現在の状態がWaitCommandでなければならない。
        if state == UsiEngineState.WaitBestmove:
            if self.engine_state != UsiEngineState.WaitCommand:
                raise ValueError(
                    "{0} : can't send go command when self.engine_state != \
                    UsiEngineState.WaitCommand".format(
                        self.instance_id
                    )
                )

        with self.state_changed_cv:
            self.engine_state = state
            self.state_changed_cv.notify_all()

    # エンジンとのやりとりを行うスレッド(read方向)
    def read_worker(self):
        while True:
            line = self.proc.stdout.readline()
            # プロセスが終了した場合、line = Noneのままreadline()を抜ける。
            if line:
                # print("engine message",line)
                self.dispatch_message(line.strip())

            # プロセスが生きているかのチェック
            retcode = self.proc.poll()
            if not line and retcode is not None:
                self.exit_state = 0
                # エラー以外の何らかの理由による終了
                break

    def reflesh_game(self) -> None:
        """
        ゲーム終了、ゲーム開始時などの初期化処理を行う
        usinewgame, gameoverコマンドを受け取ったときに呼ばれる
        """
        pass

    def send_isready_and_wait(self) -> None:
        """
        isreadyコマンドを送り、readyokを待つ
        """
        self.send_command("isready")  # 先行して"isready"を送信
        self.change_state(UsiEngineState.WaitReadyOk)
        self.wait_for_state(UsiEngineState.WaitCommand)

    # エンジンとやりとりを行うスレッド(write方向)
    def write_worker(self):

        for option in self.options:
            self.send_command(
                "setoption name {0} value {1}".format(option[0], option[1])
            )
        self.send_command("isready")  # 先行して"isready"を送信
        self.change_state(UsiEngineState.WaitReadyOk)

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
                    if self.engine_state != UsiEngineState.WaitBestmove:
                        continue
                elif token == "go":
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
                    pass
                self.proc.stdin.write(message + "\n")
                self.proc.stdin.flush()

                if token == "quit":
                    self.change_state(UsiEngineState.Disconnected)
                    # 終了コマンドを送信したなら自発的にこのスレッドを終了させる。
                    break

                retcode = self.proc.poll()
                if retcode is not None:
                    self.dead = True
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
            self.change_state(UsiEngineState.WaitCommand)
        # エンジンの読み筋に対する応答
        elif token == "info":
            if self.print_info:
                print(message, flush=True)
            self.handle_info(message)
        elif self.engine_state == UsiEngineState.PrintUSI:
            if token == "usiok":
                self.change_state(UsiEngineState.WaitCommand)
            elif not token.startswith("id"):
                self.usi_options.append(message)

    # エンジンから送られてきた"bestmove"を処理する。
    def handle_bestmove(self, message: str):
        messages = message.split()
        if len(messages) >= 4 and messages[2] == "ponder":
            self.think_result.ponder = messages[3]

        if len(messages) >= 2:
            self.think_result.bestmove = messages[1]
        else:
            # 思考内容返ってきてない。どうなってんの…。
            self.think_result.bestmove = "none"

    # エンジンから送られてきた"info ..."を処理する。
    def handle_info(self, message: str) -> None:
        # まだ"go"を発行していないのか？
        if self.think_result is None:
            return
        info: BasePlayInfo = generate_playinfo_from_info(message)
        if info is None:
            return
        while len(self.think_result.infos) < info.multipv:
            self.think_result.infos.append(None)
        self.think_result.infos[info.multipv - 1] = info

    # デストラクタで通信の切断を行う。
    def __del__(self):
        self.quit()

    def wait_for_state(self, state: UsiEngineState):
        while True:
            if self.dead:
                break
            with self.state_changed_cv:
                if self.engine_state == state:
                    return
                if self.engine_state == UsiEngineState.Disconnected:
                    # pass
                    raise ValueError("engine_state == UsiEngineState.Disconnected.")

                # Eventが変化するのを待機する。
                self.state_changed_cv.wait()

    # [SYNC] エンジンに対して1行送って、すぐに1行返ってくるので、それを待って、この関数の返し値として返す。
    def send_command_and_getline(self, command: str) -> str:
        self.wait_for_state(UsiEngineState.WaitCommand)
        self.last_received_line = None
        with self.state_changed_cv:
            self.send_cmd(command)

            # エンジン側から一行受信するまでblockingして待機
            self.state_changed_cv.wait_for(
                lambda: self.last_received_line is not None
            )
            return self.last_received_line
