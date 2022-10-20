import dataclasses
import glob
import json
import os
import random
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import shogi
from dacite import from_dict
from pytz import timezone
from sekisyu.board.get_board_from_pos_cmd import get_board_from_pos_cmd
from sekisyu.engine.base_engine import BaseEngine
from sekisyu.engine.config_engine import ConfigEngine
from sekisyu.engine.virtual_engine.base_virtual_engine import BaseVirtualEngine
from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.qgen.question_generator import generate_question_from_pos
from shogi import CSA, KIF, SQUARES, Consts

stdin_mode = False


@dataclasses.dataclass
class ConfigSekisyuEngine:
    qsa_path: str = "qsa/Qhapaq-Shogi-Academy.exe"

    # 問題を生成するパス
    ques_save_path: str = "data"
    engine_analyze: Optional[ConfigEngine] = None
    # shogiguiはスペース区切りのvalueを受け入れない様子
    analyze_go_cmd: str = "go_nodes_1000000"
    analyze_go_calc_cmd: str = "go_nodes_2020"
    analyze_go_null_cmd: str = "go_nodes_1000000"
    # こいつは処理に時間がかかるのでデフォではNoneにする
    analyze_go_null_enemy_cmd: str = ""
    null_enemy_rank: int = 1
    analyzer_multipv: int = 10

    # 評価値をこれ以上損した場合blunderとみなす
    blunder_value: int = 334

    # 敵側の評価値も計算する
    analyze_enemy: bool = True


class SekisyuEngine(BaseVirtualEngine):
    """
    指導対局エンジン。qsaの起動を介してリアルタイムで悪手とかを突っ込んでくれる。
    将棋guiや将棋神での起動も可能。リアルタイムで手を修正してもらいながら対局するを幅広いエンジンで実現することを目指す
    """

    def __init__(
        self,
        engine: BaseEngine,
        engine_analyze: Optional[BaseEngine],
        engine_name: str,
        config: Dict[str, Any],
    ) -> None:
        """
        エンジンの初期化

        engine (BaseEngine) :
            元となるエンジン。合議の場合はlistになる(多分)
        """
        self.engine = engine
        self.engine_eq = False
        if engine_analyze:
            self.engine_analyze = engine_analyze
        else:
            self.engine_eq = True
        self.engine_name = engine_name
        self.config = from_dict(data=config, data_class=ConfigSekisyuEngine)
        self.__proc_qsa = None
        self.history = {}  # 待ったの可能性を考慮し、sfenをkeyにしたdictを用意
        self.prev_history = None
        self.prev_history_pos = None
        self.ques = None
        self.battle_ts = None

    def update_ts(self):
        utc_now = datetime.now(timezone("UTC"))
        jst_now = utc_now.astimezone(timezone("Asia/Tokyo"))
        self.battle_ts = jst_now.strftime("%Y-%m-%d-%H-%M-%S")
        os.makedirs(
            f"{self.config.ques_save_path}/battle/{self.battle_ts}", exist_ok=True
        )
        os.makedirs(f"{self.config.ques_save_path}/results", exist_ok=True)

    def send_isready_and_wait(self) -> None:
        """
        isreadyコマンドを送り、readyokを待つ
        """

        # TODO electronのargの頭が悪いのでなんとかする
        self.qsa_full_path = os.path.join(os.getcwd(), self.config.qsa_path)
        with open(os.path.dirname(self.qsa_full_path) + "/cmd.txt", "w") as f:
            # text を空にする
            pass
        if self.__proc_qsa is None:
            self.__proc_qsa = subprocess.Popen(
                f"{self.qsa_full_path}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                encoding="shift-jis",
                cwd=os.path.dirname(self.qsa_full_path),
            )
            os.makedirs(self.config.ques_save_path, exist_ok=True)
        else:
            # プロセスが生きているかのチェック
            retcode = self.__proc_qsa.poll()
            if retcode is not None:
                self.__proc_qsa = subprocess.Popen(
                    f"{self.qsa_full_path}",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    encoding="shift-jis",
                    cwd=os.path.dirname(self.qsa_full_path),
                )

        self.engine.send_isready_and_wait()

    def boot(self, engine_path: str) -> None:
        """
        エンジンを起動する

        engine_path (str):
            起動するエンジンのパス
        """
        self.engine.boot(engine_path)

    def send_qsa_cmd(self, txt) -> None:
        """
        windows+electronではstdinが使えないのでファイルに書き込む
        TODO : 送ったコマンドを処理したかをどうやって処置する？少なくともsekisyu側でそれを知る手段がないように見える。
        qsaから処理したコマンドをファイルにして出力すれば一応だが、死ぬほどやりたくない
        """
        with open(
            os.path.dirname(self.qsa_full_path) + "/cmd.txt", "a", encoding="shift-jis"
        ) as f:
            f.write(f"{txt}")

    def reflesh_game(self) -> None:
        """
        ゲームを初期化する
        """
        if self.__proc_qsa is not None:
            retcode = self.__proc_qsa.poll()
            if retcode is None:
                if stdin_mode:
                    self.__proc_qsa.stdin.write(
                        f"change_alert {self.config.blunder_value}\n"
                    )
                    self.__proc_qsa.stdin.flush()
                else:
                    self.send_qsa_cmd(f"change_alert {self.config.blunder_value}\n")

        self.save_history()
        self.history = {}
        self.engine.reflesh_game()
        self.prev_history = None
        self.prev_history_pos = None
        self.ques = None
        self.update_ts()

    def save_history(self) -> None:
        if len(self.history) == 0:
            return

        output = []
        for key in self.history:
            output.append(self.history[key])
        output = {"data": output}
        with open(
            f"{self.config.ques_save_path}/results/{self.battle_ts}_history.json",
            "w",
            encoding="utf8",
        ) as f:
            json.dump(
                output,
                f,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
                separators=(",", ": "),
            )

    def get_usi_option(self) -> List[str]:
        """
        usiコマンドで出力するべきオプションを列挙する

        return:
            list(str) : 標準出力されるべきstrのリスト
        """
        opt_list = self.engine.get_usi_option()
        opt_list.append(
            f"option name SavePath type string default {self.config.ques_save_path}"
        )
        opt_list.append(
            f"option name BlunderValue type spin default {self.config.blunder_value}"
        )
        opt_list.append(
            f"option name AnalyzeCmd type string default {self.config.analyze_go_cmd}"
        )
        opt_list.append(
            f"option name AnalyzeCmdNull type string default {self.config.analyze_go_null_cmd}"
        )
        opt_list.append(
            f"option name AnalyzeCmdNullEnemy type string default {self.config.analyze_go_null_enemy_cmd}"
        )
        opt_list.append(
            f"option name NullEnemyRank type spin default {self.config.null_enemy_rank}"
        )
        opt_list.append(f"option name AnalyzeEnemy type check default true")
        opt_list.append(
            f"option name AnalyzeMultiPV type spin default {self.config.analyzer_multipv}"
        )

        return opt_list

    def set_option(self, options: List[Tuple[str, str]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """

        for opt in options:
            if opt[0] == "SavePath":
                self.config.ques_save_path = opt[1]
            elif opt[0] == "BlunderValue":
                self.config.blunder_value = int(opt[1])
            elif opt[0] == "AnalyzeCmd":
                self.config.analyze_go_cmd = opt[1]
            elif opt[0] == "AnalyzeCmdNull":
                self.config.analyze_go_null_cmd = opt[1]
            elif opt[0] == "AnalyzeCmdNullEnemy":
                self.config.analyze_go_null_enemy_cmd = opt[1]
            elif opt[0] == "NullEnemyRank":
                self.config.null_enemy_rank = int(opt[1])
            elif opt[0] == "AnalyzeMultiPV":
                self.config.analyzer_multipv = int(opt[1])
                self.engine_analyze.send_command(
                    f"setoption name MultiPV value {opt[1]}"
                )
            elif opt[0] == "AnalyzeEnemy":
                if opt[1] == "false":
                    self.config.analyze_enemy = False
                elif opt[1] == "true":
                    self.config.analyze_enemy = True
                else:
                    print("info string warning invalid bool option", opt)
            else:
                if isinstance(self.engine, BaseVirtualEngine):
                    self.engine.set_option([opt])
                else:
                    self.engine.send_command(f"setoption name {opt[0]} value {opt[1]}")

    def get_name(self) -> str:
        """
        エンジン名を取得する

        Returns:
            str: エンジン名
        """
        if self.engine_name == "":
            return self.engine.get_name()
        return self.engine_name

    def parse_pv(
        self, think_result: BasePlayInfoPack, is_ponder: bool = False
    ) -> BasePlayInfoPack:
        """
        指し手が決まった後でその局面からクイズを生成する
        """
        if (
            think_result.infos[0].pv[0] == "resign"
            or think_result.infos[0].pv[0] == "win"
        ):
            return think_result
        alert_blunder = False
        value_send = None
        pos_packet = self.position.split(" ")

        # 待ったなどにより一つ前に解析した手と異なる手を評価させられる場合、prev_historyを一旦Noneにする
        # 各種guiはプレイヤーが待ったをしたことを通知してこないため、前の自分の手番の局面を作らねば
        if self.prev_history:
            # 雑に前に出題した問題 + moveに相当するものとなっていなかった場合、待ったがあったとみなす
            if self.prev_history_pos != " ".join(pos_packet[: len(pos_packet) - 1]):
                print("info string warning invalid question. possibly matta")
                self.prev_history = None

        # 前の手を評価する。待った対策で対局毎に同じ局面は一度だけしか答えられない
        if self.prev_history:
            if self.prev_history not in self.history:
                # get ans cmd
                ans_cmd = pos_packet[-1]
                # rank and check
                rank = len(self.ques.selection_usi)
                value_send = 334
                for i, ans in enumerate(self.ques.selection_usi):
                    value_send = self.ques.values[0] - self.ques.values[i]
                    if ans_cmd == ans:
                        rank = i
                        break

                self.history[self.prev_history] = {
                    "path": self.prev_history,
                    "answer": ans_cmd,
                    "rank": rank,
                    "value": value_send,
                }

        # 子エンジンの計算結果を先に得る
        think_result = self.engine.parse_pv(think_result, is_ponder)

        # 自分の指し手についても解析を与える(optional)
        if self.config.analyze_enemy:
            pos_to_use = (
                self.position if "moves" in self.position else self.position + " moves"
            )
            print_before = self.engine_analyze.print_info

            # 解析の時のpvは表示しない
            self.engine_analyze.print_info = False
            self.ques = generate_question_from_pos(
                pos_to_use,
                self.engine_analyze,
                self.config.analyze_go_cmd.replace("_", " "),
                1,
                0,
                0,
                go_cmd_calc=self.config.analyze_go_calc_cmd.replace("_", " "),
                go_cmd_null=self.config.analyze_go_null_cmd.replace("_", " ")
                if self.config.analyze_go_null_cmd != ""
                else None,
                go_cmd_null_enemy=self.config.analyze_go_null_enemy_cmd.replace(
                    "_", " "
                )
                if self.config.analyze_go_null_enemy_cmd != ""
                else None,
                null_enemy_rank=self.config.null_enemy_rank,
            )
            self.engine_analyze.print_info = print_before

            board_sfen = (
                get_board_from_pos_cmd(pos_to_use)
                .sfen()
                .replace("/", "_")
                .replace(" ", "_")
            )
            # タイムスタンプがない場合は更新
            if self.battle_ts is None:
                self.update_ts()
            output_file_name = f"{self.config.ques_save_path}/battle/{self.battle_ts}/{board_sfen}.json"
            with open(output_file_name, "w", encoding="utf8") as f:
                json.dump(
                    dataclasses.asdict(self.ques),
                    f,
                    ensure_ascii=False,
                    indent=4,
                    sort_keys=True,
                    separators=(",", ": "),
                )

            retcode = self.__proc_qsa.poll()
            ques_fullpath = os.path.join(os.getcwd(), output_file_name)
            # print("load_quiz " + ques_fullpath+"\n")
            if retcode is None:
                if stdin_mode:
                    self.__proc_qsa.stdin.write(f"load_quiz {ques_fullpath}\n")
                    self.__proc_qsa.stdin.flush()
                else:
                    self.send_qsa_cmd(f"load_quiz {ques_fullpath}\n")

                if value_send:
                    if stdin_mode:
                        self.__proc_qsa.stdin.write(f"value {value_send}\n")
                        self.__proc_qsa.stdin.flush()
                    else:
                        self.send_qsa_cmd(f"value {value_send}\n")

            # TODO : AI側の指し手を回答に加える？
            # 待った対策をどうしよう。AI側は待ったをしないし正解率をどうせ評価しないし何も考えずに全accept?
            rank = len(self.ques.selection_usi)
            value_send = 334
            for i, ans in enumerate(self.ques.selection_usi):
                value_send = self.ques.values[0] - self.ques.values[i]
                if think_result.infos[0].pv[0] == ans:
                    rank = i
                    break

                self.history[self.prev_history] = {
                    "path": ques_fullpath,
                    "answer": think_result.infos[0].pv[0],
                    "rank": rank,
                    "value": value_send,
                }

        # 子エンジンのbestmoveから問題を生成する
        pos_to_use = (
            self.position if "moves" in self.position else self.position + " moves"
        )
        pos_to_use += f" {think_result.infos[0].pv[0]}"
        print_before = self.engine_analyze.print_info

        # 解析の時のpvは表示しない
        self.engine_analyze.print_info = False
        self.ques = generate_question_from_pos(
            pos_to_use,
            self.engine_analyze,
            self.config.analyze_go_cmd.replace("_", " "),
            1,
            0,
            0,
            go_cmd_calc=self.config.analyze_go_calc_cmd.replace("_", " "),
            go_cmd_null=self.config.analyze_go_null_cmd.replace("_", " ")
            if self.config.analyze_go_null_cmd != ""
            else None,
            go_cmd_null_enemy=self.config.analyze_go_null_enemy_cmd.replace("_", " ")
            if self.config.analyze_go_null_enemy_cmd != ""
            else None,
            null_enemy_rank=self.config.null_enemy_rank,
        )
        self.engine_analyze.print_info = print_before

        board_sfen = (
            get_board_from_pos_cmd(pos_to_use)
            .sfen()
            .replace("/", "_")
            .replace(" ", "_")
        )
        # タイムスタンプがない場合は更新
        if self.battle_ts is None:
            self.update_ts()
        output_file_name = (
            f"{self.config.ques_save_path}/battle/{self.battle_ts}/{board_sfen}.json"
        )
        with open(output_file_name, "w", encoding="utf8") as f:
            json.dump(
                dataclasses.asdict(self.ques),
                f,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
                separators=(",", ": "),
            )

        retcode = self.__proc_qsa.poll()
        ques_fullpath = os.path.join(os.getcwd(), output_file_name)
        self.prev_history_pos = pos_to_use
        self.prev_history = ques_fullpath
        # print("load_quiz " + ques_fullpath+"\n")
        if retcode is None:
            if stdin_mode:
                self.__proc_qsa.stdin.write(f"load_quiz {ques_fullpath}\n")
                self.__proc_qsa.stdin.flush()
            else:
                self.send_qsa_cmd(f"load_quiz {ques_fullpath}\n")

            if value_send:
                if stdin_mode:
                    self.__proc_qsa.stdin.write(f"value {value_send}\n")
                    self.__proc_qsa.stdin.flush()
                else:
                    self.send_qsa_cmd(f"value {value_send}\n")

        return think_result

    def send_go_and_wait(self, go_cmd: str) -> BasePlayInfoPack:
        """
        エンジンにgo コマンドを送り、bestmoveが帰ってくるまで待つ。
        接待エンジンではmultipvによって得られた複数の指し手の中から、
        重み付きランダムで一つを採択して返す。
        重みの付け方は人間の棋譜のデータ解析から得られたものを使う

        go_cmd (str):
            送られるgoコマンド。ex "go byoyomi 1000"
        """

        go_cmd_use = self.before_go_cmd(go_cmd)
        think_result = self.engine.send_go_and_wait(go_cmd_use)
        return self.parse_pv(think_result, "ponder" in go_cmd)

    def quit(self) -> None:
        """
        エンジンにquitコマンドを送る
        """
        self.save_history()
        if self.__proc_qsa is not None:
            retcode = self.__proc_qsa.poll()
            if retcode is None:
                if stdin_mode:
                    self.__proc_qsa.stdin.write("quit\n")
                    self.__proc_qsa.stdin.flush()
                else:
                    self.send_qsa_cmd("quit\n")
            else:
                with open(os.path.dirname(self.qsa_full_path) + "/cmd.txt", "w") as f:
                    # text を空にする
                    pass

        self.engine.quit()
        if not self.engine_eq:
            self.engine_analyze.quit()
