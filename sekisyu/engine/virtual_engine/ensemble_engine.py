import dataclasses
import glob
import random
from typing import Any, Dict, List, Tuple

import shogi
from dacite import from_dict
from sekisyu.engine.base_engine import BaseEngine, UsiEngineState
from sekisyu.ensemble.base_ensembler import BaseEnsembler
from sekisyu.engine.virtual_engine.base_virtual_engine import BaseVirtualEngine
from sekisyu.playout.playinfo import BasePlayInfoPack
from shogi import CSA, KIF, SQUARES, Consts
from sekisyu.ensemble.base_ensembler import BaseEnsembler

class EnsembleEngine(BaseVirtualEngine):
    
    def __init__(self, engines: List[BaseEngine], ensembler: BaseEnsembler, engine_name: str) -> None:
        """
        エンジンの初期化

        engine (BaseEngine) :
            元となるエンジン。合議の場合はlistになる(多分)
        """
        self.engines = engines
        self.engine_name = engine_name
        self.ensembler = ensembler
        self.print_info = True

    def get_name(self) -> str:
        """
        エンジン名を取得する

        Returns:
            str: エンジン名
        """
        if self.engine_name == "":
            return "ensemble_engine"
        return self.engine_name

    def boot(self, engine_path: List[str]) -> None:
        """
        エンジンを起動する

        engine_path (str):
            起動するエンジンのパス
        """
        for engine, path in zip(self.engines, engine_path):
            engine.boot(path)

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
            
    def get_state(self):
        """
        現在のエンジンの状況を出力する
        """
        # timekeeperであるengine[0]を利用する
        return self.engines[0].get_state()
    
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
        
    def set_option(self, options: List[List[Tuple[str, str]]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """
        for opt, engine in zip(options, self.engines):
            engine.set_option(opt)

    def get_option(self) -> List[List[Tuple[str, str]]]:
        """
        エンジンに送ったオプションを返す

        Returns:
            list((str, str)) : オプション一覧
        """
        output = []
        for engine in self.engines:
            output.append(engine.get_option())
        return output
    
    def send_go_and_wait(self, go_cmd: str) -> BasePlayInfoPack:
        """
        エンジンにgo コマンドを送り、bestmoveが帰ってくるまで待つ

        go_cmd (str):
            送られるgoコマンド。ex "go byoyomi 1000"
        """
        # dlshogiなどのponderを本来返さないものについても返す仕様にengine側で修正する
        for engine in self.engines[1:]:
            # idx 0 をtimekeeperとする
            engine.send_command("go infinite")
        result = self.engines[0].send_go_and_wait(go_cmd)
        return self.parse_pv(result)

    def parse_pv(self, think_result: BasePlayInfoPack) -> BasePlayInfoPack:
        """
        pvの後処理を行う。主にvirtual engineでmultipvの結果を処理して云々みたいな使い方をする
        デフォルトでは何もしない
        """
        
        # step 1 まずslaveのエンジンを全て止める
        for engine in self.engines[1:]:
            engine.send_command("stop")
            engine.wait_for_state(UsiEngineState.WaitCommand)
        
        infos = [engine.parse_pv(engine.get_current_think_result()) for engine in self.engines]
        out = self.ensembler.ensemble(infos, self.position)
        out.bestmove = out.infos[0].pv[0]
        if len(out.infos[0].pv) > 1:
            out.ponder = out.infos[0].pv[1]
        if self.print_info:
            print(out.infos[0].get_usi_str())
        return out

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
            send_all = True
        elif cmd.startswith("setoption"):
            # TODO : optionはどのengine向けかを解析して送る
            pass
        elif cmd.startswith("go"):
            self.engines[0].send_command(cmd)
            for engine in self.engines[1:]:
                # idx 0 をtimekeeperとする
                engine.send_command("go infinite")
                engine.wait_for_state(UsiEngineState.WaitBestmove)
        elif cmd.startswith("stop"):
            send_all = True
        elif cmd.startswith("ponderhit"):
            # ponderhitはmainにしか送らない
            self.engines[0].send_command(cmd)
        if send_all:
            # その他よくわからないコマンドは全部のエンジンに送る？
            # これ危険な気もする
            for engine in self.engines:
                engine.send_command(cmd)

    def reflesh_game(self) -> None:
        for engine in self.engines:
            engine.reflesh_game()

    def wait_for_state(self, state: UsiEngineState):
        self.engines[0].wait_for_state(state)

    def get_current_think_result(self) -> BasePlayInfoPack:
        """
        現時点でのpvの様子を吐く
        """
        return self.engines[0].get_current_think_result()
