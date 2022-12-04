import dataclasses
import glob
import random
from typing import Any, Dict, List, Tuple

import shogi
from dacite import from_dict
from sekisyu.engine.base_engine import BaseEngine
from sekisyu.engine.virtual_engine.base_virtual_engine import BaseVirtualEngine
from sekisyu.playout.playinfo import BasePlayInfoPack
from shogi import CSA, KIF, SQUARES, Consts


def get_piece_id(piece) -> int:
    """
    map用のコマのidを返す。
    """
    idx = piece.piece_type - 1
    if piece.color == Consts.WHITE:
        idx = idx + 14
    return idx


similar_bonus_const = [
    0.02,
    0.02,
    0.02,
    0.02,
    0.02,
    0.05,
    0.05,
    0.06,
    0.02,
    0.02,
    0.02,
    0.02,
    0.05,
    0.05,
]


def similar_bonus(idx: int) -> float:
    """
    位置が一致してる駒の数だけ点数を足す際に与えるコマごとの重み
    飛車 ... 0.05 x 2 = 0.1
    角 ... 0.05 x 2 = 0.1
    玉 ... 0.06 x 2 = 0.12
    その他 ... 34 x 0.02 = 0.68
    にしとく。
    """
    if idx >= 14:
        return similar_bonus_const[idx - 14]
    return similar_bonus_const[idx]


class BoardSimularityCalculator:
    """
    局面の類似度を計算する。
    先に教師盤面を絞り込んで9x9+持ち駒の場所に幾つコマがあるかを
    カウントした方が計算的に得なのでそれをする
    """

    def __init__(self, black_file_glob: str, white_file_glob: str) -> None:
        self.black_file_glob = black_file_glob
        self.white_file_glob = white_file_glob
        self.game_to_use_black = None
        self.game_to_use_white = None

    def reflesh_game(self):
        """
        ゲームの初期化。採択する棋譜をランダムに選ぶ
        TODO : ゲームの進行に応じて最も類似度が高い棋譜を選ぶとかしたい
        """
        if len(glob.glob(self.black_file_glob)) != 0:
            print(
                f"info string load kif file from {len(glob.glob(self.black_file_glob))} files"
            )
            self.game_to_use_black = random.choice(glob.glob(self.black_file_glob))
        else:
            print("info string kif file not found. possibly wrong path")
            self.game_to_use_black = None
        if len(glob.glob(self.white_file_glob)) != 0:
            print(
                f"info string load kif file from {len(glob.glob(self.white_file_glob))} files"
            )
            self.game_to_use_white = random.choice(glob.glob(self.white_file_glob))
        else:
            print("info string kif file not found. possibly wrong path")
            self.game_to_use_white = None

    def update_board_old(
        self,
        ply_min: int,
        ply_max: int,
        black: bool,
        ref_board,
        ignore_enemy: bool = True,
    ):
        """
        古いバージョンだが一応残しておく
        """
        # piece_type, boardを引数とする 先後 2 x コマの種類 14
        self.board_score = [[0 for i in range(81)] for j in range(28)]
        # piece_type, 枚数を引数とする 先後 2 x コマの種類 7 x 所持数(面倒なのですべて最大18枚とする)
        self.hand_score = [[0 for i in range(18)] for j in range(14)]
        if black:
            file_list = glob.glob(self.black_file_glob)
        else:
            file_list = glob.glob(self.white_file_glob)
        for file_name in file_list:
            if file_name.endswith(".csa"):
                csa_dat = CSA.Parser.parse_file(file_name)[0]
            elif file_name.endswith(".kif"):
                csa_dat = KIF.Parser.parse_file(file_name)[0]
            moves = csa_dat["moves"]
            board = shogi.Board()
            for i in range(min(ply_max, len(moves))):
                board.push(shogi.Move.from_usi(moves[i]))
                if i < ply_min:
                    continue
                sim = self.calc_board_similarity(board, ref_board, black, ignore_enemy)
                for sq in SQUARES:
                    p = board.piece_at(sq)
                    if p is None:
                        continue
                    # コマの種類に応じて加点
                    pidx: int = get_piece_id(p)

                    if ignore_enemy and black and pidx > 13:
                        continue
                    if ignore_enemy and not black and pidx < 14:
                        continue

                    self.board_score[pidx][int(sq)] += (
                        sim * sim * similar_bonus(pidx) / len(file_list)
                    )

                # 持ち駒に応じて加点
                for c in [Consts.BLACK, Consts.WHITE]:
                    if ignore_enemy and black and c == Consts.WHITE:
                        continue
                    if ignore_enemy and not black and c == Consts.BLACK:
                        continue

                    for piece_key in board.pieces_in_hand[c]:
                        pc = piece_key - 1
                        if c == Consts.BLACK:
                            self.hand_score[pc][
                                board.pieces_in_hand[c][piece_key] - 1
                            ] += (
                                sim
                                * sim
                                * similar_bonus(pc)
                                * board.pieces_in_hand[c][piece_key]
                                / len(file_list)
                            )
                        else:
                            self.hand_score[pc + 7][
                                board.pieces_in_hand[c][piece_key] - 1
                            ] += (
                                sim
                                * sim
                                * similar_bonus(pc)
                                * board.pieces_in_hand[c][piece_key]
                                / len(file_list)
                            )

    def visualize_score(self) -> None:
        """
        デバッグ用。盤面のforceを表示する
        """
        for i in range(28):
            print("type", i)
            for j in range(9):
                print(self.board_score[i][j * 9 : j * 9 + 9])

    def update_board(
        self,
        ply_min: int,
        ply_max: int,
        black: bool,
        ref_board,
        ignore_enemy: bool = True,
    ):
        # piece_type, boardを引数とする 先後 2 x コマの種類 14
        self.board_score = [[0 for i in range(81)] for j in range(28)]
        # piece_type, 枚数を引数とする 先後 2 x コマの種類 7 x 所持数(面倒なのですべて最大18枚とする)
        self.hand_score = [[0 for i in range(18)] for j in range(14)]

        # 特定のプレイヤーを真似るにあたり、棋譜の平均みたいなものをとると特徴が平均化されてしまうらしい
        # 佐藤康光九段とかの棋譜がその典型で正当居飛車と力戦振り飛車が平均された結果
        # 中途半端な居飛車をさすようになってしまう
        # そこで棋譜の中からランダムにひとつだけ選び、それを目指してもらうことにする
        # 欲を言えば相手の指し手から最も再現しやすい棋譜を選んでとかやりたいが....
        if black:
            file_name = self.game_to_use_black
        else:
            file_name = self.game_to_use_white

        # forcebookできるファイルがない時はなにもしない
        if file_name is None:
            return

        if file_name.endswith(".csa"):
            csa_dat = CSA.Parser.parse_file(file_name)[0]
        elif file_name.endswith(".kif"):
            csa_dat = KIF.Parser.parse_file(file_name)[0]
        moves = csa_dat["moves"]
        # print(moves)
        board = shogi.Board()
        for i in range(min(ply_max, len(moves))):
            board.push(shogi.Move.from_usi(moves[i]))
            if i < ply_min:
                continue
            sim = self.calc_board_similarity(board, ref_board, black, ignore_enemy)
            for sq in SQUARES:
                p = board.piece_at(sq)
                if p is None:
                    continue
                # コマの種類に応じて加点
                pidx: int = get_piece_id(p)

                if ignore_enemy and black and pidx > 13:
                    continue
                if ignore_enemy and not black and pidx < 14:
                    continue

                self.board_score[pidx][int(sq)] += sim * sim * similar_bonus(pidx)

            # 持ち駒に応じて加点
            for c in [Consts.BLACK, Consts.WHITE]:
                if ignore_enemy and black and c == Consts.WHITE:
                    continue
                if ignore_enemy and not black and c == Consts.BLACK:
                    continue

                for piece_key in board.pieces_in_hand[c]:
                    pc = piece_key - 1
                    if c == Consts.BLACK:
                        self.hand_score[pc][board.pieces_in_hand[c][piece_key] - 1] += (
                            sim
                            * sim
                            * similar_bonus(pc)
                            * board.pieces_in_hand[c][piece_key]
                        )
                    else:
                        self.hand_score[pc + 7][
                            board.pieces_in_hand[c][piece_key] - 1
                        ] += (
                            sim
                            * sim
                            * similar_bonus(pc)
                            * board.pieces_in_hand[c][piece_key]
                        )

    def calc_board_score(self, board) -> float:
        """
        board_scoreに応じて局面のボーナス値を決める
        """
        output = 0.0
        for sq in SQUARES:
            p = board.piece_at(sq)
            if p is None:
                continue
            pidx: int = get_piece_id(p)
            output += self.board_score[pidx][int(sq)]
        # 持ち駒に応じて加点。
        for c in [Consts.BLACK, Consts.WHITE]:
            for piece_key in board.pieces_in_hand[c]:
                pc = piece_key - 1
                if c == Consts.BLACK:
                    output += self.hand_score[pc][
                        board.pieces_in_hand[c][piece_key] - 1
                    ]
                else:
                    output += self.hand_score[pc + 7][
                        board.pieces_in_hand[c][piece_key] - 1
                    ]
        return output

    def calc_board_similarity(
        self, board1, board2, black: bool = True, ignore_enemy: bool = True
    ) -> float:
        """
        盤面の類似度を計算する
        """
        output = 0.0
        for sq in SQUARES:
            p = board1.piece_at(sq)
            if p is None:
                continue
            p2 = board2.piece_at(sq)
            if p2 is None:
                continue
            idx = get_piece_id(p)
            if ignore_enemy and black and idx > 13:
                continue
            if ignore_enemy and not black and idx < 14:
                continue

            if p == p2:
                output += similar_bonus(idx)

        # 持ち駒に応じて加点。
        for c in [Consts.BLACK, Consts.WHITE]:
            if ignore_enemy and black and c == Consts.WHITE:
                continue
            if ignore_enemy and not black and c == Consts.BLACK:
                continue
            for piece_key in board1.pieces_in_hand[c]:
                pc = piece_key - 1
                output += similar_bonus(pc) * min(
                    board1.pieces_in_hand[c][piece_key],
                    board2.pieces_in_hand[c][piece_key],
                )
        if ignore_enemy:
            return output * 2.0
        return output


@dataclasses.dataclass
class ConfigForceEngine:
    # 使用する棋譜ファイル。ワイルドカkードあり
    kif_file_black: str = "kif/black/*"
    kif_file_white: str = "kif/white/*"

    # 類似度によって得られる補正。
    # 最終的な評価値は 評価値 + min(max_bonus, Σ_局面 類似度^2 x bonus)とする?
    # 2乗にするのは線形にするとあまり似ていない局面の影響を受けるから
    # または、局面類似度にしきい値をキメて、xx以下は無視とかにするか？
    bonus_amp: float = 500.0
    max_bonus: float = 1.0
    # bookに加える手数
    ply_min: int = 0
    ply_max: int = 200

    # 類似度計算のときに相手の盤面を考慮する
    ignore_enemy: bool = True

    # 許容できる評価値の下限
    min_score: int = -300
    # forcebook中のMultiPV
    forcebook_mutipv: int = 30
    # forcebookが終わった後のmultipv
    normal_multipv: int = 1

    # forcebookのときに評価値にランダムノイズを加えるなら
    eval_random_noise: int = 0

    # 定跡が当たった場合はそのまま指す
    use_book: bool = True

    # 棋力調整用のレーティング。時々意図的に悪い手を指させるためにnodesをランダムに変える
    node_max: int = 20000
    # 探索node数は node_maxからnode_max x 2^{-node_range} まで対数分布で推移する
    node_range: int = 5
    # 本気を出すか否かのスイッチ
    max_level: bool = True

    # 手の良し悪しを判別して悪手をアラームするか
    alert_bad_move: bool = False
    # 手の良し悪しを判別するためのgo_cmdの条件
    alert_go_cmd = "go depth 15"
    # 悪い手と判断する基準(評価値)
    alert_th: int = 300

    # blunderをする最小手数
    blunder_ply_min: int = 0

    # 評価値の値域
    eval_min: int = -3000
    eval_max: int = 3000
    eval_range: int = 300

    # レーティングの値域
    rate_range: List[int] = None
    # 一致率のリストi番目のレートのj番目の一致率
    accuracy_list: List[List[float]] = None
    # 悪手の値域
    blunder_range: List[int] = None
    # 悪手のマトリックスi番目のレートのj番目のk番目の悪手のマトリックス
    blunder_matrix: List[List[List[float]]] = None

    # forcebookを用いる最大手数
    forcebook_ply_max: int = 16
    loss_limit: int = 300


class ForceBookEngine(BaseVirtualEngine):
    """
    棋風トレースエンジンのクラス

    USIプロトコルを介し、対局や各種局面の解析を行う。
    このエンジンでは特定の対局から棋風を学びそれに近い手を指させることを目指す
    """

    def __init__(
        self, engine: BaseEngine, engine_name: str, config: Dict[str, Any]
    ) -> None:
        """
        エンジンの初期化

        engine (BaseEngine) :
            元となるエンジン。合議の場合はlistになる(多分)
        """
        self.engine = engine
        self.engine_name = engine_name
        self.config: ConfigForceEngine = from_dict(
            data_class=ConfigForceEngine, data=config
        )

        # print(self.engine_name, "level", self.config.level)
        self.bn = BoardSimularityCalculator(
            self.config.kif_file_black, self.config.kif_file_white
        )
        self.engine.change_multipv(self.config.forcebook_mutipv)
        self.pv_changed = False

    def boot(self, engine_path: str) -> None:
        """
        エンジンを起動する

        engine_path (str):
            起動するエンジンのパス
        """
        self.engine.boot(engine_path)
        # multipvをデフォで入れておく
        self.reflesh_game()

    def get_usi_option(self) -> List[str]:
        """
        usiコマンドで出力するべきオプションを列挙する

        return:
            list(str) : 標準出力されるべきstrのリスト
        """
        opt_list = self.engine.get_usi_option()
        # 棋風のデータ
        opt_list.append("option name KifBlack type string default kif/black/*")
        opt_list.append("option name KifWhite type string default kif/white/*")
        opt_list.append("option name MPVBook type spin default 30 min 1 max 800")
        opt_list.append("option name MPVMoves type spin default 16 min 1 max 300")
        opt_list.append("option name MPVStrength type spin default 500 min 0 max 10000")

        # 手加減具合
        # 現状やねうら王側に任せる。nodesを絞った探索が一番それっぽい手加減ができてるように見えるから
        opt_list.append(
            "option name LevelMax type spin default 2022 min 100 max 20000000"
        )
        opt_list.append("option name LevelRange type spin default 5 min 1 max 10")
        # 手加減なしモード
        opt_list.append("option name MaxLevel type check default true")
        return opt_list

    def set_option(self, options: List[Tuple[str, str]]) -> None:
        """
        エンジンにオプションを送る

        options list((str, str)):
            USIプロトコルによってオプションを設定する
            setoption name options[i][0] value options[i][1]
        """

        for opt in options:
            # if opt[0] == "Level":
            #     self.config.level = int(opt[1])
            if opt[0] == "MaxLevel":
                self.config.max_level = opt[1]
            elif opt[0] == "NodeMax":
                self.config.node_max = int(opt[1])
            elif opt[0] == "NodeRange":
                self.config.node_range = int(opt[1])
            if opt[0] == "KifBlack":
                self.config.kif_file_black = opt[1]
                self.bn = BoardSimularityCalculator(
                    self.config.kif_file_black, self.config.kif_file_white
                )
            elif opt[0] == "KifWhite":
                self.config.kif_file_white = opt[1]
                self.bn = BoardSimularityCalculator(
                    self.config.kif_file_black, self.config.kif_file_white
                )
            elif opt[0] == "MPVBook":
                self.config.forcebook_mutipv = int(opt[1])
            elif opt[0] == "MPVMoves":
                self.config.forcebook_ply_max = int(opt[1])
            elif opt[0] == "MPVStrength":
                self.config.bonus_amp = float(opt[1])

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

    def send_command(self, cmd: str) -> None:
        """
        エンジンに特別なコマンドを送る。
        """
        if cmd.startswith("go"):
            self.before_go_cmd(cmd)
        elif cmd.startswith("setoption"):
            option = cmd.split(" ")
            self.set_option([(option[2], option[4])])
            return

        super().send_command(cmd)

    def reflesh_game(self) -> None:
        """
        ゲーム終了、ゲーム開始時などの初期化処理を行う
        usinewgame, gameoverコマンドを受け取ったときに呼ばれる
        """
        self.bn.reflesh_game()
        self.engine.change_multipv(self.config.forcebook_mutipv)
        self.pv_changed = False

    def change_result_by_forcebook(self, board, think_result):

        self.bn.update_board(
            self.config.ply_min,
            self.config.ply_max,
            board.turn == Consts.BLACK,
            board,
            self.config.ignore_enemy,
        )
        # 類似度ベースの盤面ボーナスを計算する
        max_score = -float("inf")
        max_id = 0
        for i, candidate in enumerate(think_result.infos):
            # 悪すぎる手は除去する
            if (
                candidate.pv[0] != think_result.bestmove
                and candidate.eval < self.config.min_score
            ):
                continue
            if (
                candidate.pv[0] != think_result.bestmove
                and think_result.infos[0].eval - candidate.eval > self.config.loss_limit
            ):
                continue

            board.push(shogi.Move.from_usi(candidate.pv[0]))
            bonus = self.bn.calc_board_score(board)
            value = (
                candidate.eval
                + bonus * self.config.bonus_amp
                + random.randint(0, self.config.eval_random_noise)
            )
            # print("info string ", candidate.pv[0] ,candidate.eval, bonus, value)
            if value > max_score:
                max_id = i
                max_score = value
            board.pop()
        think_result.bestmove = think_result.infos[max_id].pv[0]
        print(f"info string max_id changed to {max_id}")
        # print(think_result.infos[max_id].pv[0])

    def get_eval_idx(self, eval: int) -> int:
        """
        現在の評価値がeval_idxの何番目に相当するかを求める
        """
        if eval < self.config.eval_min:
            return 0
        elif eval > self.config.eval_max:
            return (
                1
                + (self.config.eval_max - self.config.eval_min)
                // self.config.eval_range
            )
        return 1 + (eval - self.config.eval_min) // self.config.eval_range

    def switch_pv(self):
        """
        手数を調べて必要ならmultipvを変化させる
        """
        moves = self.position.split(" ")
        if len(moves) - 3 >= self.config.forcebook_ply_max and not self.pv_changed:
            self.engine.change_multipv(self.config.normal_multipv)
            print("pv changed", self.config.normal_multipv)
            self.pv_changed = True

    def parse_pv(
        self, think_result: BasePlayInfoPack, is_ponder: bool = False
    ) -> BasePlayInfoPack:
        """
        forcebookの後処理をする
        think_result (BasePlayInfoPack) : 通常のエンジンでよませた時の結果
        """
        print(self.config.forcebook_ply_max, "plymax")
        moves = self.position.split(" ")
        # 定跡を指したか確認する。全ての手のevalが0だったら定跡（bad hack）
        use_book = True
        for candidate in think_result.infos:
            if candidate.eval != 0:
                use_book = False
                break
        if use_book and self.config.use_book:
            print("info string bookhit")
            return think_result

        if self.config.alert_bad_move and not is_ponder:
            print("info string alert mode")
            # 前の指し手がない場合はalertができない
            moves = self.position.split(" ")
            if len(moves) > 3:

                # 前の局面の評価
                move_prev = moves[-1]
                prev_pos = " ".join(moves[:-1])
                self.engine.send_command(prev_pos)
                think_result_prev = self.engine.send_go_and_wait(
                    self.config.alert_go_cmd
                )

                # 今の局面の評価
                self.engine.send_command(self.position)
                think_result_curr = self.engine.send_go_and_wait(
                    self.config.alert_go_cmd
                )

                if (
                    think_result_curr.infos[0].eval + think_result_prev.infos[0].eval
                    > self.config.alert_th
                ):
                    print("info string alert bad move")
                    print("your_move ", move_prev)
                    print("better_move", think_result_prev.infos[0].pv[0])

        # forcebookを使わない場合
        if len(moves) - 3 >= self.config.forcebook_ply_max:
            return think_result
        else:
            # forcebookで指し手を決める
            board = shogi.Board()
            if len(moves) > 3:
                moves = moves[3:]
                for mv in moves:
                    board.push(shogi.Move.from_usi(mv))
            self.change_result_by_forcebook(board, think_result)

        return think_result

    def before_go_cmd(self, go_cmd):
        """
        go_cmdを呼ぶ前の処理
        """
        self.switch_pv()
        if not self.config.max_level:
            # TODO : レーティングとノード数の式を決める
            rate_level = random.randint(0, self.config.node_range)
            nodes = self.config.node_max
            for _ in range(rate_level):
                nodes = int(nodes / 2)
            print(f"info string node changed to {nodes}")
            return f"go nodes {nodes}"
        return go_cmd

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


if __name__ == "__main__":
    # position startpos moves 7g7f 8c8d 6i7h 4a3b 3g3f 3c3d 3i4h 8d8e 2h3h 8e8f 8g8f 8b8f
    from sekisyu.engine.yaneuraou_engine import YaneuraOuEngine

    # bn = BoardSimularityCalculator("dataset/ysmt/black/*.csa", "dataset/ysmt/white/*.csa", 200) # noqa
    # bn.visualize_score()
    engine = YaneuraOuEngine()
    engine.set_option([("Threads", "2"), ("BookFile", "no_book"), ("MultiPV", "10")])
    engine.boot("dataset/bin/yaneuraou/YaneuraOu-by-gcc")
    fb_engine = ForceBookEngine(
        engine,
        "forcebook",
        {
            "kif_file_black": "dataset/kubo/black/*.csa",
            "kif_file_white": "dataset/kubo/white/*.csa",
        },
    )
    engine.send_command("position startpos moves 7g7f 3c3d 1g1f 8c8d 6g6f 8d8e")
    fb_engine.send_go_and_wait("go byoyomi 2000")
