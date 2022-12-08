from typing import List, Optional, Tuple

from sekisyu.engine.base_engine import BaseEngine, UsiEngineState
from sekisyu.engine.virtual_engine.base_virtual_engine import BaseVirtualEngine
from sekisyu.playout.playinfo import BasePlayInfoPack


class RelayEngine(BaseVirtualEngine):
    def __init__(
        self, engines: List[BaseEngine], ply_to_pass: List[int], engine_name: str
    ) -> None:
        """
        エンジンの初期化

        engine (BaseEngine) :
            元となるエンジン。リレーを担当するエンジンたち
        """
        self.engines = engines
        self.engine_name = engine_name
        self.ply_to_pass = ply_to_pass
        self.print_info = True
        assert len(self.ply_to_pass) + 1 == len(self.engines)
        self.engine_to_use = self.engines[0]

    def get_engine_to_use(self, pos_cmd: str) -> BaseEngine:
        ply = 0
        if "moves" in pos_cmd:
            ply = len(pos_cmd.split(" ")) - 2
        for i in range(len(self.ply_to_pass)):
            if self.ply_to_pass[i] > ply:
                return self.engines[i]
        return self.engines[-1]

    def get_name(self) -> str:
        """
        エンジン名を取得する

        Returns:
            str: エンジン名
        """
        if self.engine_name == "":
            return "relay_engine"
        return self.engine_name

    def boot_relay(self, engine_path: List[str]) -> None:
        """
        エンジンを起動する

        engine_path (str):
            起動するエンジンのパス
        """
        for engine, path in zip(self.engines, engine_path):
            engine.boot(path)

    def boot(self, engine_path: str) -> None:
        raise NotImplementedError

    def send_isready_and_wait(self) -> None:
        """
        isreadyコマンドを送り、readyokを待つ
        """
        for engine in self.engines:
            engine.send_isready_and_wait()

    def quit(self) -> None:
        """
        エンジンにquitコマンドを送る
        """
        for engine in self.engines:
            engine.quit()

    def set_print_info(self, print_info: bool) -> None:
        """
        エンジンのログ出力に関する設定を行う。
        Trueにすることでエンジンからの標準出力のうちinfoから始まるものが出力される

        print_info(bool):
            Trueにすることでエンジンからの標準出力のうちinfoから始まるものが出力される
        """
        self.print_info = print_info
        for engine in self.engines:
            engine.set_print_info(print_info)

    def get_state(self) -> Optional[UsiEngineState]:
        """
        現在のエンジンの状況を出力する
        """
        # timekeeperであるengine[0]を利用する
        return self.engine_to_use.get_state()

    def get_usi_option(self) -> List[str]:
        """
        usiコマンドで出力するべきオプションを列挙する

        return:
            list(str) : 標準出力されるべきstrのリスト
        """
        output = []
        for i, engine in enumerate(self.engines):
            opts = engine.get_usi_option()
            for opt in opts:
                output.append(f"engine_{i}_{opt}")
        return output

    # エンジンのconnect()が呼び出されたあとであるか
    def is_connected(self) -> bool:
        for engine in self.engines:
            if not engine.is_connected():
                return False
        return True

    def set_option(self, options: List[Tuple[str, str]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """
        raise NotImplementedError

    def set_option_relay(self, options: List[List[Tuple[str, str]]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """
        for opt, engine in zip(options, self.engines):
            engine.set_option(opt)

    def get_option_relay(self) -> List[List[Tuple[str, str]]]:
        """
        エンジンに送ったオプションを返す

        Returns:
            list((str, str)) : オプション一覧
        """
        output = []
        for engine in self.engines:
            output.append(engine.get_option())
        return output

    def get_option(self) -> List[Tuple[str, str]]:
        """
        エンジンのオプションを返す

        Returns:
            list((str, str)) : オプション一覧
        """
        raise NotImplementedError

    def send_go_and_wait(self, go_cmd: str) -> BasePlayInfoPack:
        """
        エンジンにgo コマンドを送り、bestmoveが帰js26ってくるまで待つ

        go_cmd (str):
            送られるgoコマンド。ex "go byoyomi 1000"
        """
        # dlshogiなどのponderを本来返さないものについても返す仕様にengine側で修正する
        result = self.engine_to_use.send_go_and_wait(go_cmd)
        return self.parse_pv(result)

    def parse_pv(
        self, think_result: BasePlayInfoPack, is_ponder: bool = False
    ) -> BasePlayInfoPack:
        """
        pvの後処理を行う。主にvirtual engineでmultipvの結果を処理して云々みたいな使い方をする
        デフォルトでは何もしない
        """
        if len(think_result.infos[0].pv) > 1:
            think_result.ponder = think_result.infos[0].pv[1]
        if self.print_info:
            print(think_result.infos[0].get_usi_str())
        return think_result

        return think_result

    def send_command(self, cmd: str) -> None:
        """
        エンジンに特別なコマンドを送る。
        この部分がアンサンブル特有で面倒くさい
        """
        send_all = False
        if cmd == "gameover" or cmd == "usinewgame":
            self.reflesh_game()
        elif cmd.startswith("position"):
            self.position = cmd
            self.engine_to_use = self.get_engine_to_use(cmd)
            self.engine_to_use.send_command(cmd)
        elif cmd.startswith("setoption"):
            # TODO : optionはどのengine向けかを解析して送る
            pass
        elif cmd.startswith("go"):
            self.engine_to_use.send_command(cmd)
        elif cmd.startswith("stop"):
            self.engine_to_use.send_command(cmd)
        elif cmd.startswith("ponderhit"):
            self.engine_to_use.send_command(cmd)

    def reflesh_game(self) -> None:
        for engine in self.engines:
            engine.reflesh_game()
        self.engine_to_use = self.engines[0]

    def wait_for_state(self, state: UsiEngineState) -> None:
        self.engine_to_use.wait_for_state(state)

    def get_current_think_result(self) -> BasePlayInfoPack:
        """
        現時点でのpvの様子を吐く
        """
        return self.engine_to_use.get_current_think_result()
