import dataclasses
from dataclasses import field
from typing import List, Optional

from sekisyu.kif_analyzer.config_kif_analyzer import ConfigAnalysis


@dataclasses.dataclass
class ConfigAccuracyPack:
    """
    手の一致率に関する解析結果の解析条件を纏めたもの。
    異なる解析結果を比較する際にここの値を比べることでその正当性をチェックする
    """

    # 解析に使ったconfig
    config_analysis: Optional[ConfigAnalysis] = None

    # 手数毎に一致率を取得するときの手の刻み幅と最大値
    ply_range: int = 20
    ply_max: int = 100

    # 評価値ごとに一致率を取得するときの手の刻み幅と最大値
    eval_min: int = -3000
    eval_max: int = 3000
    eval_range: int = 300

    # これよりも評価値が良い場合は詰み＝頓死とみなす
    sudden_death_value: int = 2021

    # 解析時に見るmultipv
    multipv: int = 5


@dataclasses.dataclass
class AccuracyPack:
    """
    手の一致率に関する解析結果まとめ
    """

    # 解析の設定
    config: ConfigAccuracyPack

    # 以下解析結果

    # [i][j] ... 手数が[j]の状態で指し手が[i]位の手と一致した回数。i=-1はランク外に相当
    rank_count: List[List[int]] = field(default_factory=list)
    # その確率表示
    rank_count_prod: List[List[float]] = field(default_factory=list)

    # [i][j] ... 評価値が[j]の状態で指し手が[i]位の手と一致した回数。i=-1はランク外に相当
    rank_count_eval: List[List[int]] = field(default_factory=list)
    # その確率表示
    rank_count_prod_eval: List[List[float]] = field(default_factory=list)

    # 見た局面の総数
    # ply_sum: List[int] = field(default_factory=list)

    # 詰みを見逃した回数
    miss_mate_count: int = 0

    # 見た詰み局面の総数
    ply_mate_sum: int = 0

    # 頓死チェックに使った局面の数
    ply_sudden_death: int = 0

    # 頓死した局面数
    sudden_death_count: int = 0

    # 棋譜の数
    kif_count: int = 0

    def load_config(self, config: ConfigAccuracyPack) -> None:
        self.config = config
        self.rank_count = [
            [0 for _ in range(config.ply_max // config.ply_range + 1)]
            for _ in range(config.multipv + 1)
        ]
        self.rank_count_prod = [
            [0 for _ in range(config.ply_max // config.ply_range + 1)]
            for _ in range(config.multipv + 1)
        ]
        self.rank_count_eval = [
            [
                0
                for _ in range(
                    2 + (config.eval_max - config.eval_min) // config.eval_range
                )
            ]
            for _ in range(config.multipv + 1)
        ]
        self.rank_count_prod_eval = [
            [
                0
                for _ in range(
                    2 + (config.eval_max - config.eval_min) // config.eval_range
                )
            ]
            for _ in range(config.multipv + 1)
        ]

    def calc_prod(self) -> None:
        """
        確率計算をする。rank_count, rank_count_evalからrank_count_prod, rank_count_prod_evalを計算する
        """

        for ply_idx in range(self.config.ply_max // self.config.ply_range + 1):
            cnt_sum = 0.0001
            for rank_idx in range(self.config.multipv + 1):
                cnt_sum += self.rank_count[rank_idx][ply_idx]
            for rank_idx in range(self.config.multipv + 1):
                self.rank_count_prod[rank_idx][ply_idx] = float(
                    self.rank_count[rank_idx][ply_idx] / cnt_sum
                )

        for eval_idx in range(
            2 + (self.config.eval_max - self.config.eval_min) // self.config.eval_range
        ):
            cnt_sum = 0.0001
            for rank_idx in range(self.config.multipv + 1):
                cnt_sum += self.rank_count_eval[rank_idx][eval_idx]
            for rank_idx in range(self.config.multipv + 1):
                self.rank_count_prod_eval[rank_idx][eval_idx] = float(
                    self.rank_count_eval[rank_idx][eval_idx] / cnt_sum
                )
