import copy
import os
import random
import time
from datetime import datetime
from enum import IntEnum

from pytz import timezone
from sekisyu.battle.config_battle import ConfigBattle
from sekisyu.battle.draw_checker import draw_check_from_go_cmd
from sekisyu.engine.base_engine import BaseEngine
from sekisyu.playout.log_scanner import Scanner
from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.playout.playout import BasePlayOut, GameResult


# 手番を表現するEnum
class Turn(IntEnum):
    BLACK = 0  # 先手
    WHITE = 1  # 後手

    # 反転させた手番を返す
    def flip(self) -> int:  # Turn:
        return Turn(int(self) ^ 1)


# 1対1での対局を管理してくれる補助クラス
class BattleServer:
    def __init__(
        self, engine1: BaseEngine, engine2: BaseEngine, config: ConfigBattle
    ) -> None:

        # --- public members ---

        # 1P側、2P側のエンジンを生成して代入する。
        # デフォルトでは先手が1P側、後手が2P側になる。
        # self.is_2p_black == Trueのときはこれが反転する。
        # ※　与えた開始局面のsfenが先手番から始まるとは限らないので注意。
        self.engines = [engine1, engine2]

        # --- publc readonly members
        self.config: ConfigBattle = config

        # configのinitial_pos_listがファイル名であることを想定する
        if len(self.config.initial_pos_list) > 0:
            if os.path.exists(self.config.initial_pos_list[0]):
                initial_pos_list = []
                for file_name in self.config.initial_pos_list:
                    with open(file_name) as f:
                        initial_pos_list.extend(f.readlines())

        # 現在の手番側
        self.side_to_move = Turn.BLACK

        # 現在の局面のsfen("startpos moves ..."や、"sfen ... move ..."の形)
        self.sfen = "startpos"

        # 開始局面からの手数
        self.game_ply = 1

        # 現在のゲーム状態
        # ゲームが終了したら、game_result.is_gameover() == Trueになる。
        self.game_result = GameResult.INIT

        # --- private memebers ---

        # 持ち時間残り [1P側 , 2P側] 単位はms。
        self.__rest_time = [0, 0]

        # 対局の持ち時間設定
        # self.set_time_setting()で渡されたものをparseしたもの。
        self.__time_setting = {}

        # 対局用スレッド
        self.__game_thread = None

        # 対局用スレッドの強制停止フラグ
        self.__stop_thread = False

        self.is_2p_black = False

    # turn側のplayer番号を取得する。(is_2p_blackを考慮する。)
    # 返し値
    # 0 : 1P側
    # 1 : 2P側
    def player_number(self, turn: Turn) -> int:
        if self.is_2p_black:
            turn = turn.flip()
        return int(turn)

    # turn側のplayer名を取得する。(is_2p_blackを考慮する)
    # "1p" , "2p"という文字列が返る。
    def player_str(self, turn: Turn) -> str:
        return str(self.player_number(turn) + 1) + "p"

    # turn手番側のエンジンを取得する
    # is_2p_black == Trueのときは、先手側がengines[1]、後手側がengines[0]になるので注意。
    def engine(self, turn: Turn) -> BaseEngine:
        return self.engines[self.player_number(turn)]

    # turn手番側の持ち時間の残り。
    # self.__rest_timeはis_2p_blackの影響を受ける。
    def rest_time(self, turn: Turn) -> int:
        return self.__rest_time[self.player_number(turn)]

    # 持ち時間設定を行う
    # time = 先後の持ち時間[ms]
    # time1p = 1p側 持ち時間[ms](1p側だけ個別に設定したいとき)
    # time2p = 2p側 持ち時間[ms](2p側だけ個別に設定したいとき)
    # byoyomi = 秒読み[ms]
    # byoyomi1p = 1p側秒読み[ms]
    # byoyomi2p = 2p側秒読み[ms]
    # inc = 1手ごとの加算[ms]
    # inc1p = 1p側のinc[ms]
    # inc2p = 2p側のinc[ms]
    #
    # 例 : "byoyomi 100" : 1手0.1秒
    # 例 : "time 900000" : 15分
    # 例 : "time1p 900000 time2p 900000 byoyomi 5000" : 15分 + 秒読み5秒
    # 例 : "time1p 10000 time2p 10000 inc 5000" : 10秒 + 1手ごとに5秒加算
    # 例 : "time1p 10000 time2p 10000 inc1p 5000 inc2p 1000" : 10秒 + 先手1手ごとに5秒、後手1手ごとに1秒加算
    def set_time_setting(self, setting: str):
        scanner = Scanner(setting.split())
        tokens = [
            "time",
            "time1p",
            "time2p",
            "byoyomi",
            "byoyomi1p",
            "byoyomi2p",
            "inc",
            "inc1p",
            "inc2p",
        ]
        time_setting = {}

        while not scanner.is_eof():
            token = scanner.get_token()
            param = scanner.get_token()
            # 使えない指定がないかのチェック
            if token not in tokens:
                raise ValueError("invalid token : " + token)
            int_param = int(param)
            time_setting[token] = int_param

        # "byoyomi"は"byoyomi1p","byoyomi2p"に敷衍する。("time" , "inc"も同様)
        for s in ["time", "byoyomi", "inc"]:
            if s in time_setting:
                inc_param = time_setting[s]
                time_setting[s + "1p"] = inc_param
                time_setting[s + "2p"] = inc_param

        # 0になっている項目があるとややこしいので0埋めしておく。
        for token in tokens:
            if token not in time_setting:
                time_setting[token] = 0

        self.__time_setting = time_setting

    def play_one_game(self):

        # ゲーム対局中ではないか？これは前提条件の違反
        if self.game_result == GameResult.PLAYING:
            raise ValueError("must be gameover.")

        # 局面をランダムに選ぶ
        if len(self.config.initial_pos_list) > 0:
            sfen = random.choice(self.config.initial_pos_list)
        else:
            sfen = "position startpos moves"
        sfen = sfen.replace("\n", "")

        if "position" not in sfen:
            sfen = "position " + sfen

        # 局面の設定
        if "moves" not in sfen:
            sfen += " moves"

        self.sfen = sfen
        initial_ply = len(sfen.split(" ")) - 2
        if initial_ply % 2 == 1:
            self.side_to_move = Turn.BLACK
        else:
            self.side_to_move = Turn.WHITE
        self.game_ply = initial_ply

        for engine in self.engines:
            engine.send_isready_and_wait()  # やねうら王は毎回isreadyを読んだほうがいい？
            engine.send_command("usinewgame")  # いまから対局はじまるよー

        for engine in self.engines:
            if not engine.is_connected():
                raise ValueError("engine is not connected.")

        self.game_result = GameResult.PLAYING

        # 開始時 持ち時間
        if self.config.time_by_player:
            self.__rest_time = [self.config.time_player[0], self.config.time_player[1]]
        else:
            if self.is_2p_black:
                self.__rest_time = [self.config.wtime, self.config.btime]
            else:
                self.__rest_time = [self.config.btime, self.config.wtime]

        # self.__game_thread = threading.Thread(target=self.__game_worker)
        # self.__game_thread.start()
        return self.__game_worker()

    # 対局スレッド
    def __game_worker(self):
        engine_black = self.engine(Turn.BLACK)
        engine_white = self.engine(Turn.WHITE)
        utc_now = datetime.now(timezone("UTC"))
        jst_now = utc_now.astimezone(timezone("Asia/Tokyo"))
        ts = jst_now.strftime("%Y-%m-%d-%H-%M-%S")
        playout = BasePlayOut(
            engine_option=(engine_black.get_option(), engine_white.get_option()),
            initial_pos=self.sfen,
            timestamp=ts,
            player_name=(engine_black.get_name(), engine_white.get_name()),
            game_config=self.config,
            tags=self.config.tags,
        )
        if len(self.sfen.split(" ")) > 3:
            playout.plys = copy.deepcopy(self.sfen.split(" ")[3:])
        while self.game_ply < self.config.moves_to_draw:

            # 手番側に属するエンジンを取得する
            # ※　is_2p_black == Trueのときは相手番のほうのエンジンを取得するので注意。
            engine = self.engine(self.side_to_move)
            # engine_waiting = self.engine(self.side_to_move.flip())
            # 千日手を発見
            if draw_check_from_go_cmd(self.sfen):
                self.game_result = GameResult.DRAW
                playout.result = self.game_result
                break

            engine.send_command(self.sfen)

            # 現在の手番を数値化したもの。1P側=0 , 2P側=1
            int_turn = self.player_number(self.side_to_move)

            byoyomi = 0
            incs = [0, 0]
            if self.config.time_by_player:
                if self.config.inc_player[0] == 0:
                    byoyomi = self.config.byoyomi_player[int_turn]
                else:
                    incs = [
                        self.config.inc_player[self.player_number(Turn.BLACK)],
                        self.config.inc_player[self.player_number(Turn.WHITE)],
                    ]
            else:
                byoyomi = self.config.byoyomi
                incs = [self.config.inc_time, self.config.inc_time]

            if byoyomi == 0:
                byoyomi_or_inctime_str = "binc {0} winc {1}".format(incs[0], incs[1])
            else:
                byoyomi_or_inctime_str = "byoyomi {0}".format(byoyomi)

            start_time = time.time()
            play_info: BasePlayInfoPack = engine.send_go_and_wait(
                "go btime {0} wtime {1} {2}".format(
                    self.rest_time(Turn.BLACK),
                    self.rest_time(Turn.WHITE),
                    byoyomi_or_inctime_str,
                )
            )
            playout.playinfo_list.append(play_info.copy())
            playout.plys.append(play_info.bestmove)
            end_time = time.time()

            # 使用した時間を1秒単位で繰り上げて、残り時間から減算
            # プロセス間の通信遅延を考慮して300[ms]ほど引いておく。(秒読みの場合、どうせ使い切るので問題ないはず..)
            # 0.3秒以内に指すと0秒で指したことになるけど、いまのエンジン、詰みを発見したとき以外そういう挙動にはなりにくいのでまあいいや。
            elapsed_time = (
                end_time - start_time
            ) - self.config.virtual_delay  # [ms]に変換
            elapsed_time = int(elapsed_time + 0.999) * 1000
            if elapsed_time < 0:
                elapsed_time = 0

            self.__rest_time[int_turn] -= int(elapsed_time)
            if (
                self.__rest_time[int_turn] < -0.0 and self.config.lose_timeup
            ):  # -2秒より減っていたら。0.1秒対局とかもあるので1秒繰り上げで引いていくとおかしくなる。
                self.game_result = GameResult.from_timeup(self.side_to_move)
                self.__game_over()
                # 本来、自己対局では時間切れになってはならない。(計測が不確かになる)
                # 警告を表示しておく。
                print("Error! : player timeup")
                return
            # 残り時間がわずかにマイナスになっていたら0に戻しておく。
            if self.__rest_time[int_turn] < 0:
                self.__rest_time[int_turn] = 0

            bestmove = play_info.bestmove
            if bestmove == "resign":
                # 相手番の勝利
                self.game_result = GameResult.from_resign(self.side_to_move)
                playout.result = self.game_result
                self.__game_over()
                return playout
            if bestmove == "win":
                # 宣言勝ち(手番側の勝ち)
                # 局面はノーチェックだが、まあエンジン側がバグっていなければこれでいいだろう)
                self.game_result = GameResult.from_declare(self.side_to_move)
                playout.result = self.game_result
                self.__game_over()
                return playout
            self.sfen = self.sfen + " " + bestmove
            self.game_ply += 1

            # inctime分、時間を加算
            self.__rest_time[int_turn] += incs[self.side_to_move]
            self.side_to_move = self.side_to_move.flip()
            # 千日手引き分けを処理しないといけないが、ここで判定するのは難しいので
            # max_movesで抜けることを期待。

            if self.__stop_thread:
                # 強制停止なので試合内容は保証されない
                self.game_result = GameResult.STOP_GAME
                playout.result = self.game_result
                return playout

        # 引き分けで終了
        if self.game_result != GameResult.DRAW:
            self.game_result = GameResult.MAX_MOVES
        playout.result = self.game_result
        self.__game_over()
        return playout

    # ゲームオーバーの処理
    # エンジンに対してゲームオーバーのメッセージを送信する。
    def __game_over(self):
        result = self.game_result
        if result.is_draw():
            for engine in self.engines:
                engine.send_command("gameover draw")
        elif result.is_black_win():
            self.engine(Turn.BLACK).send_command("gameover win")
            self.engine(Turn.WHITE).send_command("gameover lose")
        elif result.is_white_win():
            self.engine(Turn.WHITE).send_command("gameover win")
            self.engine(Turn.BLACK).send_command("gameover lose")
        else:
            # それ以外サポートしてない
            raise ValueError("illegal result")

    # エンジンを終了させるなどの後処理を行う
    def terminate(self):
        self.__stop_thread = True
        # self.__game_thread.join()
        for engine in self.engines:
            engine.quit()

    # エンジンを終了させる
    def __del__(self):
        self.terminate()
