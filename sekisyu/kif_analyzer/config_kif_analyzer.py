import dataclasses

from sekisyu.engine.config_engine import ConfigEngine


@dataclasses.dataclass
class ConfigAnalysis:
    """
    解析条件を格納する。

    engine_config (ConfigEngine):
        エンジンの設定
    go_time (int):
        解析に使う時間。単位はミリ秒
    """

    engine_config: ConfigEngine
    go_time: int = 1000
    go_nodes: int = 0
