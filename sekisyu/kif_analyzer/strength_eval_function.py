import dataclasses
from typing import List

from sekisyu.kif_analyzer.accuracy_pack import AccuracyPack, ConfigAccuracyPack


@dataclasses.dataclass
class StrengthData:
    """
    レーティングの計算結果
    """

    # accuracy_pack計算時の条件
    config_accuracy_pack: ConfigAccuracyPack

    # 手数の状態がiの状態での強さ
    strength_ply: List[int]

    # 評価値の状態がiの状態での強さ
    strength_eval: List[int]


@dataclasses.dataclass
class StrengthEvalFunction:
    """
    レーティングの評価関数
    """

    # accuracy_pack計算時の条件
    config_accuracy_pack: ConfigAccuracyPack

    # i番目のプレイヤーのaccuracy_list
    accuracy_pack_list: List[AccuracyPack]

    # i番目のプレイヤーの強さ（eloレーティングであることが多い）
    strength_list: List[int]


def dot(xs, ys):
    """
    numpyのdotが使えないので泣く泣く実装
    """
    out = 0.0
    for (x, y) in zip(xs, ys):
        out += x * y
    return out


def mul(xs, value):
    """
    numpyの*演算子が使えないので泣く泣く実装
    """
    return [x * v for (x, v) in zip(xs, value)]


def get_linear_param(x, y, weight):
    """
    weightで重み付けされた最小二乗法で線形補間を行い、y=ax+bを得る
    """
    n = sum(weight)
    x_w = mul(x, weight)
    y_w = mul(y, weight)
    print(x_w, y_w)
    a = (dot(x_w, y) - sum(y_w) * sum(x_w) / n) / (dot(x_w, x) - sum(x_w) ** 2 / n)
    b = (sum(y_w) - a * sum(x_w)) / n
    return a, b


def get_wl_expectation(x_data, y_data, pred_x, scale):
    """
    重み付きの線形補間で予測値を得る
    """
    weights = []
    xw = (max(x_data) - min(x_data)) * scale
    for x in x_data:
        d = float(abs(x - pred_x) / xw)
        if d < 1.0:
            weights.append(1.0)
        else:
            weights.append(1.0 / d)
    a, b = get_linear_param(x_data, y_data, weights)
    return a * pred_x + b


def expect_rate(eval_func: StrengthEvalFunction, acc: AccuracyPack) -> StrengthData:
    """
    レートを予測する。与えられた各データについて重みつきの最小二乗法で線形補間する
    面白いから進行や評価値毎にレーティングを計算する
    """

    # TODO config_accyracy_packが一致するかをチェック

    strength_ply: List[int] = []
    strength_eval: List[int] = []

    # 進行に関するレート計算
    for i in range(len(eval_func.accuracy_pack_list[0].rank_count_prod)):
        prod_list = []
        for ac_eval in eval_func.accuracy_pack_list:
            prod_list.append(ac_eval.rank_count_prod[0][i])
        strength_ply.append(
            get_wl_expectation(
                prod_list, eval_func.strength_list, acc.rank_count_prod[0][i], 0.15
            )
        )

    # 評価値に関するレート計算
    for i in range(len(eval_func.accuracy_pack_list[0].rank_count_prod_eval)):
        prod_list = []
        for ac_eval in eval_func.accuracy_pack_list:
            prod_list.append(ac_eval.rank_count_prod_eval[0][i])
        strength_eval.append(
            get_wl_expectation(
                prod_list, eval_func.strength_list, acc.rank_count_prod_eval[0][i], 0.15
            )
        )

    return StrengthData(
        config_accuracy_pack=eval_func.config_accuracy_pack,
        strength_ply=strength_ply,
        strength_eval=strength_eval,
    )
