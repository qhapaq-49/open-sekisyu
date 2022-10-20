import tempfile
from typing import Optional

from sekisyu.csa.csa import playout_to_csa_v22
from sekisyu.engine.base_engine import BaseEngine
from sekisyu.kif_analyzer.config_kif_analyzer import ConfigAnalysis
from sekisyu.kif_labeler.kif_labels_getter import get_kif_label_from_kif_data
from sekisyu.playout.playinfo import BasePlayInfoPack
from sekisyu.playout.playout import BasePlayOut


def get_go_cmd(config: ConfigAnalysis) -> str:
    if config.go_time > 0:
        return "go byoyomi " + str(config.go_time)
    return "go nodes " + str(config.go_nodes)


def analyze_playout(
    playout: BasePlayOut,
    engine: BaseEngine,
    config: ConfigAnalysis,
    json_name: str = "",
    csa_name: str = "",
    label_data_name="",
    original_csa_name: Optional[str] = None,
) -> None:
    """
    playoutを解析する。現状ではplayoutのevalinfo_listを書き換える

    engine (BaseEngine):
        解析に用いたエンジン

    playout (BasePlayOut):
        解析するplayout

    config (ConfigAnalysis):
        解析の設定

    json_name (str):
        解析結果のjsonの保存先

    label_data_name (str):
        これが空文字以外の場合、そのyamlを利用して棋譜のラベルを生成する
    """
    playout.config_analysis = config
    playout.evalinfo_list = []
    sfen = "position startpos moves "
    engine.send_command(sfen)
    play_info: BasePlayInfoPack = engine.send_go_and_wait(get_go_cmd(config))
    playout.evalinfo_list.append(play_info.copy())
    for move_str in playout.plys:
        sfen += move_str + " "
        engine.send_command(sfen)
        play_info: BasePlayInfoPack = engine.send_go_and_wait(get_go_cmd(config))
        playout.evalinfo_list.append(play_info.copy())

    if not original_csa_name:
        with tempfile.TemporaryDirectory() as temp_dir:
            playout_to_csa_v22(playout, temp_dir + "/temp.csa")
            tags = get_kif_label_from_kif_data(
                temp_dir + "/temp.csa", label_data_name=label_data_name
            )
            tag_to_add = []
            for tag in tags:
                tag_to_add.append(tag.name)
    else:
        tags = get_kif_label_from_kif_data(
            original_csa_name, label_data_name=label_data_name
        )
        tag_to_add = []
        for tag in tags:
            tag_to_add.append(tag.name)

    playout.tags = tag_to_add
    if json_name != "":
        playout.to_json(json_name)
    if csa_name != "":
        playout_to_csa_v22(playout, csa_name)
