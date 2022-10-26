from typing import Tuple

import shogi
from sekisyu.kif_labeler.game_info import GameInfo
from sekisyu.title_parse.title_parse import remove_title


def get_title_alias_year_kif(kif_file_name: str) -> Tuple[str, str, str]:
    """
    kifファイルから棋戦名、リンク、対局年を返す

    kif_file_name (str) : csaのファイル名

    return:
        リンク、対局年、棋戦名の順番でstrを返す
    """

    alias = ""
    year = "????"
    title = ""

    kif_txt: str = open(kif_file_name, encoding="shift-jis", errors="ignore").read()

    # kifファイルについては現状alias属性を与えていない
    alias = kif_file_name

    # 開始日時のタグがあればそこから取得
    year_id = kif_txt.find("開始日時：")
    if year_id != -1:
        end_year_id = kif_txt.find("\n", year_id)
        year = kif_txt[year_id + 5 : end_year_id]
        # 年号は4桁とする
        if len(year) < 4:
            print(year)
            year = "????"
            # raise ValueError

    # イベントのタグがあればそこから取得
    title_id = kif_txt.find("イベント：")
    if title_id != -1:
        end_title_id = kif_txt.find("\n", title_id)
        title = kif_txt[title_id + 5 : end_title_id]

    return alias, year, title


def get_title_alias_year_csa(csa_file_name: str) -> Tuple[str, str, str]:
    """
    csaファイルから棋戦名、リンク、対局年を返す

    csa_file_name (str) : csaのファイル名

    return:
        リンク、対局年、棋戦名の順番でstrを返す
    """
    alias = ""
    year = "????"
    title = ""

    csa_txt: str = open(csa_file_name).read()
    alias_id = csa_txt.find("$ALIAS:")

    if alias_id != -1:
        # aliasがあるときはaliasを取得する
        end_alias_id = csa_txt.find("\n", alias_id)
        alias = csa_txt[alias_id + 7 : end_alias_id]
    else:
        # ない場合はファイル名を返す
        alias = csa_file_name

    # starttimeが与えられていればそこから対局年を取得できる。ない場合は空文字
    year_id = csa_txt.find("$START_TIME:")
    if year_id != -1:
        end_year_id = csa_txt.find("\n", year_id)
        year = csa_txt[year_id + 12 : end_year_id]
        # 年号は4桁とする
        if len(year) < 4:
            print(year)
            year = "????"
            # raise ValueError

    # eventが与えられていればそこから棋戦名を取得できる。ない場合は空文字
    title_id = csa_txt.find("$EVENT:")
    if title_id != -1:
        end_title_id = csa_txt.find("\n", title_id)
        title = csa_txt[title_id + 7 : end_title_id]

    return alias, year, title


def game_info_getter(file_name: str) -> GameInfo:
    if file_name.endswith(".csa"):
        alias, year, title = get_title_alias_year_csa(file_name)
        kif = shogi.CSA.Parser.parse_file(file_name)[0]
    elif file_name.endswith(".kif"):
        alias, year, title = get_title_alias_year_kif(file_name)
        kif = shogi.KIF.Parser.parse_file(file_name)[0]

    black_name = remove_title(kif["names"][shogi.BLACK])
    white_name = remove_title(kif["names"][shogi.WHITE])
    kif_result = kif["win"]
    is_draw = False
    if kif_result == "b":
        is_black_win = True
    elif kif_result == "w":
        is_black_win = False
    else:
        is_black_win = True
        is_draw = True

    return GameInfo(
        year + "-" + black_name + "-" + white_name + "-" + title,
        black_name,
        white_name,
        is_draw,
        is_black_win,
        alias,
        year[0:4],
        title,
    )
