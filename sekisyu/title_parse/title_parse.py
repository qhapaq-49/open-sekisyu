import re
from typing import List, Optional

remove_list = [
    "九段",
    "八段",
    "七段",
    "六段",
    "五段",
    "四段",
    "三段",
    "二段",
    "初段",
    "1級",
    "2級",
    "3級",
    "4級",
    "5級",
    "6級",
    "7級",
    "8級",
    "9級",
    "１級",
    "２級",
    "３級",
    "４級",
    "５級",
    "６級",
    "７級",
    "８級",
    "９級",
    "名人",
    "竜王",
    "叡王",
    "王位",
    "王座",
    "棋聖",
    "棋王",
    "王将",
    "銀河",
    "NHK杯",
    "ＪＴ杯覇者",
    "JT杯覇者",
    "女流",
    "永世",
    "名誉",
    "女王",
    "清麗",
    "倉敷藤花",
    "二冠",
    "三冠",
    "四冠",
    "五冠",
    "六冠",
    "七冠",
    "八冠",
    "勝ち",
    "負け",
    "引き分け",
    " ",
    "(",
    ")",
    "（",
    "）",
    "　",
    "・",
    "\n",
]


def remove_title(original_name: str) -> str:
    """
    xx 初段などの肩書を除去した文字列を返す

    Args:
        original_name (str) : 肩書つきの名前（例：羽生善治七冠）
    Returns:
        str 肩書を除去した名前（例；羽生善治）
    """
    output = original_name
    for rl in remove_list:
        output = output.replace(rl, "")
    return output


def search_filter(
    name: str,
    filter_names: List[str],
    upgrade: bool = False,
    remove_title_upgrade: bool = True,
) -> Optional[int]:
    """
    対局者の名前がフィルタのどれかに合致するかを検索する。
    複数のフィルタに合致する場合、idxが一番若いものが返される

    name (str) : 検索対象の名前
    filter_names (str) : 正規表現で書かれたフィルタ名
    upgrade(bool) : TrueにするとNoneを返す代わりにfilterに値を足してくれる
    remove_title_upgrade(bool) : Trueにするとupgradeするときにtitleを除去する

    return :
        int : filter_nameのどれかに合致する場合そのidx。何にも合致しない場合 None
    """

    for idx, filt in enumerate(filter_names):
        if filt == name:
            return idx
        try:
            m = re.search(filt, name)
        except Exception:
            continue
        if m is not None:
            return idx
    if upgrade:
        if remove_title_upgrade:
            filter_names.append(remove_title(name))
        else:
            filter_names.append(name)
        # print("new name appended", filter_names[-1])
        return len(filter_names) - 1
    return None
