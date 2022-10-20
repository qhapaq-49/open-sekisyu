from typing import Any, Dict

from sekisyu.ensemble.base_ensembler import BaseEnsembler
from sekisyu.ensemble.positive_ensembler import PositiveEnsembler
from sekisyu.ensemble.yane_dl_ensembler import YaneDLEnsembler, YaneDLEnsemblerPositive


def generate_ensembler_dict(config: Dict[str, Any]) -> BaseEnsembler:
    """
    あんさんブラーの生成 from dict

    Args:
        config (dict(str, any)): エンジンの条件


    Returns:
        BaseEnsembler : エンジン
    """
    if config["ensembler_mode"] == "positive":
        return PositiveEnsembler(
            config.get("bonus"),
            config.get("bonus_by_ply"),
            config.get("bonus_by_eval"),
            config.get("book_th"),
        )
    elif config["ensembler_mode"] == "yanedl":
        return YaneDLEnsembler(config["bonus_ratio"])
    elif config["ensembler_mode"] == "yanedl_positive":
        return YaneDLEnsemblerPositive(config["bonus_a"], config["bonus_b"])
    raise ValueError
