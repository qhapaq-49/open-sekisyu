import tempfile
from typing import Any, Dict, List

import shogi
import yaml
from sekisyu.csa.csa import playout_to_csa_v22
from sekisyu.kif_labeler.game_info import GameInfo, generate_kif_labels
from sekisyu.kif_labeler.game_info_getter import game_info_getter
from sekisyu.kif_labeler.kif_label import KifLabel
from sekisyu.playout.playout import BasePlayOut
from shogi import SQUARES, Move
from shogi.Piece import Piece

SQUARE_DICT_FROM_USI = {
    "9a": 0,
    "8a": 1,
    "7a": 2,
    "6a": 3,
    "5a": 4,
    "4a": 5,
    "3a": 6,
    "2a": 7,
    "1a": 8,
    "9b": 9,
    "8b": 10,
    "7b": 11,
    "6b": 12,
    "5b": 13,
    "4b": 14,
    "3b": 15,
    "2b": 16,
    "1b": 17,
    "9c": 18,
    "8c": 19,
    "7c": 20,
    "6c": 21,
    "5c": 22,
    "4c": 23,
    "3c": 24,
    "2c": 25,
    "1c": 26,
    "9d": 27,
    "8d": 28,
    "7d": 29,
    "6d": 30,
    "5d": 31,
    "4d": 32,
    "3d": 33,
    "2d": 34,
    "1d": 35,
    "9e": 36,
    "8e": 37,
    "7e": 38,
    "6e": 39,
    "5e": 40,
    "4e": 41,
    "3e": 42,
    "2e": 43,
    "1e": 44,
    "9f": 45,
    "8f": 46,
    "7f": 47,
    "6f": 48,
    "5f": 49,
    "4f": 50,
    "3f": 51,
    "2f": 52,
    "1f": 53,
    "9g": 54,
    "8g": 55,
    "7g": 56,
    "6g": 57,
    "5g": 58,
    "4g": 59,
    "3g": 60,
    "2g": 61,
    "1g": 62,
    "9h": 63,
    "8h": 64,
    "7h": 65,
    "6h": 66,
    "5h": 67,
    "4h": 68,
    "3h": 69,
    "2h": 70,
    "1h": 71,
    "9i": 72,
    "8i": 73,
    "7i": 74,
    "6i": 75,
    "5i": 76,
    "4i": 77,
    "3i": 78,
    "2i": 79,
    "1i": 80,
}


def get_square_from_usi(square_str: str, flip: bool = False) -> SQUARES:
    """
    usi形式の局面からpython-shogiのinputを吐く

    TODO : これよく使うのでpython-shogiにprする
    """
    if flip:
        return 80 - SQUARE_DICT_FROM_USI[square_str]
    return SQUARE_DICT_FROM_USI[square_str]


def get_piece_from_csa(piece_str: str, flip: bool = False):
    piece = Piece.from_symbol(piece_str)
    if flip:
        # flipで駒を反転
        piece.color ^= 1
    return piece


def get_move_from_usi(move_str: str, flip: bool = False) -> Move:
    if not flip:
        return Move.from_usi(move_str)

    move_original = Move.from_usi(move_str)

    # 駒打ちならpieceを反転させる
    if "*" in move_str:
        move_original.to_square = get_square_from_usi(move_str[2:], flip=True)
        return move_original

    move_original.from_square = get_square_from_usi(move_str[0:2], flip=True)
    move_original.to_square = get_square_from_usi(move_str[2:], flip=True)
    return move_original


def check_label(
    data: Dict[str, Any], board, tags_exist, tesuu: int, flip: bool = False
) -> bool:
    """
    局面とタグのペアを与えて、その局面がタグの条件を満たしているかを判別する
        pieces: "盤上の駒[AND条件]",
        hand: "駒台の駒[AND条件]",
        hand_exclude: "駒台にあってはいけない駒[NOT OR条件]",
        moves: "指し手[OR条件]",
        capture: "捕獲した駒[OR条件]",
        tags_required: "成立に必要なタグ[AND条件]",
        tags_exclude:
          "そのタグが既に存在していたら成立扱いにしない[NOT OR条件]",
        tags_disable: "無効化させるタグ",
        special: "特殊",
        tesuu_max: "最大手数制限",
        hide: "非表示",
        noturn: "先手番/後手番のルール対生成をしない",
    """
    if "special" in data:
        return False

    if "tesuu_max" in data:
        if float(data["tesuu_max"]) < tesuu:
            return False

    if "tags_required" in data:
        for t in data["tags_required"]:
            if t not in tags_exist:
                return False

    if "tags_exclude" in data:
        for t in data["tags_exclude"]:
            if t in tags_exist:
                return False

    if "pieces" in data:
        for p in data["pieces"]:
            piece_str = p[0]
            square_str = p[2:]
            square = get_square_from_usi(square_str, flip)
            piece = get_piece_from_csa(piece_str, flip)
            if piece != board.piece_at(square):
                return False

    if "hand" in data:
        for h in data["hand"]:
            piece = get_piece_from_csa(h, flip)
            if not board.has_piece_in_hand(piece.piece_type, piece.color):
                return False

    if "hand_exclude" in data:
        for h in data["hand_exclude"]:
            piece = get_piece_from_csa(h, flip)
            if board.has_piece_in_hand(piece.piece_type, piece.color):
                return False

    if "moves" in data:
        if tesuu == 0:
            return False
        last_move = board.pop()
        reject = True
        for m in data["moves"]:
            piece_str = m[0]
            piece = get_piece_from_csa(piece_str, flip)
            move_str = m[2:]
            if get_move_from_usi(
                move_str, flip
            ) == last_move and piece == board.piece_at(last_move.from_square):
                reject = False
                break
        board.push(last_move)
        if reject:
            return False

    if "capture" in data:
        reject = True
        last_move = board.pop()
        c_piece = board.piece_at(last_move.to_square)
        for c in data["capture"]:
            piece = get_piece_from_csa(c, flip)
            if c_piece == piece:
                reject = False
                break
        board.push(last_move)
        if reject:
            return False

    return True


def get_kif_label_from_kif_data(
    file_name, label_data_name: str = "sekisyu/kif_labeler/label_data.yaml"
) -> List[KifLabel]:
    """
    python-shogi形式の棋譜データからラベルを取得する
    """

    if file_name.endswith(".csa"):
        kif = shogi.CSA.Parser.parse_file(file_name)[0]
    elif file_name.endswith(".kif"):
        kif = shogi.KIF.Parser.parse_file(file_name)[0]

    with open(label_data_name) as f:
        data_all = yaml.safe_load(f)

    tags_ok_ja = set()
    tags_ok_id = set()
    tags_remove = set()
    board = shogi.Board(kif["sfen"])
    game_info: GameInfo = game_info_getter(file_name)
    output = generate_kif_labels(game_info)

    for data in data_all:
        is_ok_tag = False
        if "noturn" not in data:
            is_ok_tag = check_label(data, board, tags_ok_id, 0, flip=False)
            if is_ok_tag:
                tags_ok_ja.add("先手" + data["name"]["ja_JP"])
                tags_ok_id.add(data["id"])
            is_ok_tag = check_label(data, board, tags_ok_id, 0, flip=True)
            if is_ok_tag:
                tags_ok_ja.add("後手" + data["name"]["ja_JP"])
                tags_ok_id.add(data["id"])
        else:
            is_ok_tag = check_label(data, board, tags_ok_id, 0)
            if is_ok_tag:
                tags_ok_ja.add(data["name"]["ja_JP"])
                tags_ok_id.add(data["id"])
        if is_ok_tag and "tags_disable" in data:
            for d in data["tags_disable"]:
                tags_remove.add(d)
    for i in range(len(kif["moves"])):
        board.push_usi(kif["moves"][i])
        for data in data_all:
            if data["id"] in tags_remove:
                continue
            is_ok_tag = False
            if "noturn" not in data:
                is_ok_tag = check_label(data, board, tags_ok_id, i, flip=False)
                if is_ok_tag:
                    tags_ok_ja.add("先手" + data["name"]["ja_JP"])
                    tags_ok_id.add(data["id"])
                is_ok_tag = check_label(data, board, tags_ok_id, i, flip=True)
                if is_ok_tag:
                    tags_ok_ja.add("後手" + data["name"]["ja_JP"])
                    tags_ok_id.add(data["id"])
            else:
                is_ok_tag = check_label(data, board, tags_ok_id, i)
                if is_ok_tag:
                    tags_ok_ja.add(data["name"]["ja_JP"])
                    tags_ok_id.add(data["id"])
            if is_ok_tag and "tags_disable" in data:
                for d in data["tags_disable"]:
                    tags_remove.add(d)
    # print(tags_ok_ja)

    for tag in tags_ok_ja:
        output.append(KifLabel(name=tag))
    return output


def get_kif_label_from_playout(
    playout: BasePlayOut,
    label_data_name: str = "sekisyu/kif_labeler/label_data.yaml",
    reuse_json: bool = True,
    overwrite_playout: bool = True,
) -> List[KifLabel]:
    """
    playoutからラベルを取得する。
    playoutから一時的にcsaファイルを出力してそれを読み込ませるという雑なソリューション
    """
    if len(playout.tags) > 0 and reuse_json:
        return [KifLabel(name=tag) for tag in playout.tags]
    with tempfile.TemporaryDirectory() as tdict:
        playout_to_csa_v22(playout, f"{tdict}/temp.csa")
        tags = get_kif_label_from_kif_data(f"{tdict}/temp.csa")
    if overwrite_playout:
        playout.tags = [tag.name for tag in tags]
    return tags


def test2():
    print(get_move_from_usi("7g7f", flip=False))
    print(get_move_from_usi("7g7f", flip=True))
    print(get_move_from_usi("B*8c", flip=False))
    print(get_move_from_usi("B*8c", flip=True))


def test1():
    # test
    import glob

    kif_names = glob.glob("/home/shiku/AI/shogi/sekisyu/dataset/fujiis/*/*.csa")
    for kif_name in kif_names:
        print(kif_name)
        get_kif_label_from_kif_data(kif_name)


if __name__ == "__main__":
    test2()
