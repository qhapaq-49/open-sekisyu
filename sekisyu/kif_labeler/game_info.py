from typing import List

from sekisyu.kif_labeler.kif_label import KifLabel
from sekisyu.title_parse.title_parse import remove_title


class GameInfo:
    """
    ゲームの基本的な情報を格納したもの

    対局時期、大会名、勝者敗者、ファイルの格納場所に関する情報を含む
    """

    def __init__(
        self,
        game_title,
        black_pl,
        white_pl,
        is_draw,
        is_black_win,
        alias,
        year,
        title,
        is_remove_title: bool = True,
    ):
        self.game_title = game_title
        if is_remove_title:
            self.black_pl = remove_title(black_pl)
            self.white_pl = remove_title(white_pl)
        else:
            self.black_pl = black_pl
            self.white_pl = white_pl
        self.is_draw = is_draw
        self.is_black_win = is_black_win
        self.year = year + "年"
        self.title = title
        self.alias = alias


def generate_kif_labels(game_info: GameInfo) -> List[KifLabel]:
    """
    ゲームの情報から棋譜のラベルを出力する

    game_info (GameInfo) : ゲームの情報

    return:
        list (KifLabel) : 棋譜のラベルのリスト
    """

    output = []
    output.append(KifLabel(name=game_info.year, description="対局が行われた年"))
    if game_info.title != "":
        output.append(KifLabel(name=game_info.title, description="棋戦名"))
    output.append(KifLabel(name=game_info.black_pl, description="プレイヤー名に関する条件"))
    output.append(KifLabel(name=game_info.white_pl, description="プレイヤー名に関する条件"))

    output.append(
        KifLabel(name=game_info.black_pl + "先手", description="プレイヤーの先後に関する条件")
    )
    output.append(
        KifLabel(name=game_info.white_pl + "後手", description="プレイヤーの先後に関する条件")
    )

    if game_info.is_draw:
        output.append(KifLabel(name="引き分け", description="千日手、持将棋、手数制限などによる引き分け"))
        output.append(
            KifLabel(name=game_info.black_pl + "引き分け", description="プレイヤーの対戦結果")
        )
        output.append(
            KifLabel(name=game_info.white_pl + "引き分け", description="プレイヤーの対戦結果")
        )
    else:
        if game_info.is_black_win:
            output.append(KifLabel(name="先手勝ち", description="先手勝ちで対局が終了した"))
            output.append(
                KifLabel(name=game_info.black_pl + "勝ち", description="プレイヤーの対戦結果")
            )
            output.append(
                KifLabel(name=game_info.white_pl + "負け", description="プレイヤーの対戦結果")
            )
        else:
            output.append(KifLabel(name="後手勝ち", description="後手勝ちで対局が終了した"))
            output.append(
                KifLabel(name=game_info.black_pl + "負け", description="プレイヤーの対戦結果")
            )
            output.append(
                KifLabel(name=game_info.white_pl + "勝ち", description="プレイヤーの対戦結果")
            )
    return output
