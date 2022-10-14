from typing import List, Tuple

from sekisyu.engine.base_engine import BaseEngine, UsiEngineState
from sekisyu.playout.playinfo import BasePlayInfoPack


class BaseVirtualEngine(BaseEngine):
    """
    合議、クラスタ、接待などエンジンの指し手や評価値を解析して指し手を決めるエンジンのモック
    """

    def __init__(self, engine: BaseEngine, engine_name: str) -> None:
        """
        エンジンの初期化

        engine (BaseEngine) :
            元となるエンジン。合議の場合はlistになる(多分)
        """
        self.dead = False
        self.engine = engine
        self.engine_name = engine_name

    def get_name(self) -> str:
        """
        エンジン名を取得する

        Returns:
            str: エンジン名
        """
        if self.engine_name == "":
            return self.engine.get_name()
        return self.engine_name

    def boot(self, engine_path: str) -> None:
        """
        エンジンを起動する

        engine_path (str):
            起動するエンジンのパス
        """
        self.engine.boot(engine_path)

    def send_isready_and_wait(self) -> None:
        """
        isreadyコマンドを送り、readyokを待つ
        """
        self.engine.send_isready_and_wait()

    def set_print_info(self, print_info: bool) -> None:
        """
        エンジンのログ出力に関する設定を行う。
        Trueにすることでエンジンからの標準出力のうちinfoから始まるものが出力される

        print_info(bool):
            Trueにすることでエンジンからの標準出力のうちinfoから始まるものが出力される
        """
        self.engine.set_print_info(print_info)

    def get_state(self):
        """
        現在のエンジンの状況を出力する
        """
        return self.engine.get_state()

    def get_usi_option(self) -> List[str]:
        """
        usiコマンドで出力するべきオプションを列挙する

        return:
            list(str) : 標準出力されるべきstrのリスト
        """
        return self.engine.get_usi_option()

    # エンジンのconnect()が呼び出されたあとであるか
    def is_connected(self) -> bool:
        return self.engine.is_connected

    def quit(self) -> None:
        """
        エンジンにquitコマンドを送る
        """
        self.engine.quit()

    def set_option(self, options: List[Tuple[str, str]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """
        self.engine.set_option(options)

    def get_option(self) -> List[Tuple[str, str]]:
        """
        エンジンのオプションを返す

        Returns:
            list((str, str)) : オプション一覧
        """
        return self.engine.get_option()

    def get_current_think_result(self) -> BasePlayInfoPack:
        """
        現時点でのpvの様子を吐く
        """
        return self.engine.get_current_think_result()

    def parse_pv(self, think_result: BasePlayInfoPack) -> BasePlayInfoPack:
        """
        pvの後処理を行う。主にvirtual engineでmultipvの結果を処理して云々みたいな使い方をする
        デフォルトでは何もしない
        """
        return self.engine.parse_pv(think_result)

    def send_go_and_wait(self, go_cmd: str) -> BasePlayInfoPack:
        """
        エンジンにgo コマンドを送り、bestmoveが帰ってくるまで待つ

        go_cmd (str):
            送られるgoコマンド。ex "go byoyomi 1000"
        """
        raise NotImplementedError

    def reflesh_game(self) -> None:
        self.engine.reflesh_game()

    def send_command(self, cmd: str) -> None:
        """
        エンジンに特別なコマンドを送る。
        """
        if cmd == "gameover" or cmd == "usinewgame":
            self.reflesh_game()
        if cmd.startswith("position"):
            self.position = cmd
        if cmd.startswith("setoption"):
            print(f"info string {cmd}")
            option = cmd.split(" ")
            if len(option) > 4:
                self.set_option([(option[2], " ".join(option[4:]))])
            else:
                self.set_option([(option[2], "")])
            return
        self.engine.send_command(cmd)

    # self.engine_stateを変更する。
    def change_state(self, state: UsiEngineState):
        raise NotImplementedError

    # エンジンとのやりとりを行うスレッド(read方向)
    def read_worker(self):
        raise NotImplementedError

    # エンジンとやりとりを行うスレッド(write方向)
    def write_worker(self):
        raise NotImplementedError

    # エンジン側から送られてきたメッセージを解釈する。
    def dispatch_message(self, message: str):
        raise NotImplementedError

    # エンジンから送られてきた"bestmove"を処理する。
    def handle_bestmove(self, message: str):
        raise NotImplementedError

    # エンジンから送られてきた"info ..."を処理する。
    def handle_info(self, message: str) -> None:
        raise NotImplementedError

    # デストラクタで通信の切断を行う。
    def __del__(self):
        self.quit()

    def wait_for_state(self, state: UsiEngineState):
        self.engine.wait_for_state(state)
