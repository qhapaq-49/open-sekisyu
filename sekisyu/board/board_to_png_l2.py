import dataclasses
import textwrap
from pathlib import Path
from typing import Tuple

import PIL
import shogi
from PIL import Image, ImageDraw, ImageOps
from shogi import SQUARES, Board, Consts


@dataclasses.dataclass
class ConfigBoard:
    """
    盤面描画用のconfig
    """

    # 将棋盤の画像
    board: str = "assets/visualize/board/board.jpg"

    # font path
    font_path: str = "/usr/share/fonts/OTF/TakaoPMincho.ttf"
    font_size: int = 20
    font_x_margin: int = 40
    font_y_margin: int = 0

    # 駒の画像
    pawn_black: str = "assets/visualize/koma/pawn.png"
    lance_black: str = "assets/visualize/koma/lance.png"
    knight_black: str = "assets/visualize/koma/knight.png"
    silver_black: str = "assets/visualize/koma/silver.png"
    gold_black: str = "assets/visualize/koma/gold.png"
    bishop_black: str = "assets/visualize/koma/bishop.png"
    rook_black: str = "assets/visualize/koma/rook.png"
    king_black: str = "assets/visualize/koma/king.png"

    pro_pawn_black: str = "assets/visualize/koma/pro_pawn.png"
    pro_lance_black: str = "assets/visualize/koma/pro_lance.png"
    pro_knight_black: str = "assets/visualize/koma/pro_knight.png"
    pro_silver_black: str = "assets/visualize/koma/pro_silver.png"
    pro_bishop_black: str = "assets/visualize/koma/pro_bishop.png"
    pro_rook_black: str = "assets/visualize/koma/pro_rook.png"

    pawn_white: str = "assets/visualize/koma/pawn.png"
    lance_white: str = "assets/visualize/koma/lance.png"
    knight_white: str = "assets/visualize/koma/knight.png"
    silver_white: str = "assets/visualize/koma/silver.png"
    gold_white: str = "assets/visualize/koma/gold.png"
    bishop_white: str = "assets/visualize/koma/bishop.png"
    rook_white: str = "assets/visualize/koma/rook.png"
    king_white: str = "assets/visualize/koma/eking.png"

    pro_pawn_white: str = "assets/visualize/koma/pro_pawn.png"
    pro_lance_white: str = "assets/visualize/koma/pro_lance.png"
    pro_knight_white: str = "assets/visualize/koma/pro_knight.png"
    pro_silver_white: str = "assets/visualize/koma/pro_silver.png"
    pro_bishop_white: str = "assets/visualize/koma/pro_bishop.png"
    pro_rook_white: str = "assets/visualize/koma/pro_rook.png"

    # 先手と後手で同じ駒を使う
    use_same_piece: bool = False

    # 将棋盤の大きさ
    board_width: int = 600
    board_height: int = 640

    # 将棋盤と駒のオフセット
    piece_offset_x: int = 30
    piece_offset_y: int = 30

    # 盤面の横幅と縦幅
    piece_width: int = 60
    piece_height: int = 64
    # 駒が一路進むたびに動く長さ
    piece_x: int = 60
    piece_y: int = 64

    hand_height: int = 60

    # 盤面に対するxy方向の余白
    x0_offset: int = 0
    x1_offset: int = 0
    y0_offset: int = 0
    y1_offset: int = 400

    # バックグラウンドの色
    bg_color: Tuple[int, int, int] = (255, 255, 255)
    hand_color: Tuple[int, int, int] = (128, 128, 128)

    text_width: int = 32


def get_koma_str(config: ConfigBoard, idx: int) -> str:
    koma_str = [
        config.pawn_black,
        config.lance_black,
        config.knight_black,
        config.silver_black,
        config.gold_black,
        config.bishop_black,
        config.rook_black,
        config.king_black,
        config.pro_pawn_black,
        config.pro_lance_black,
        config.pro_knight_black,
        config.pro_silver_black,
        config.pro_bishop_black,
        config.pro_rook_black,
        config.pawn_white,
        config.lance_white,
        config.knight_white,
        config.silver_white,
        config.gold_white,
        config.bishop_white,
        config.rook_white,
        config.king_white,
        config.pro_pawn_white,
        config.pro_lance_white,
        config.pro_knight_white,
        config.pro_silver_white,
        config.pro_bishop_white,
        config.pro_rook_white,
    ]
    if config.use_same_piece:
        return koma_str[idx % 14]
    return koma_str[idx]


def calc_board_xy(config: ConfigBoard) -> Tuple[int, int]:
    """
    将棋盤の位置を計算する
    """
    return config.x0_offset, config.y0_offset + config.hand_height


def calc_koma_xy(config: ConfigBoard, rank: int, row: int) -> Tuple[int, int]:
    """
    盤面上のrank, rowで指定された場所のxyを返す
    """
    board_x, board_y = calc_board_xy(config)
    return (
        board_x + config.piece_offset_x + config.piece_x * row,
        board_y + config.piece_offset_y + config.piece_y * rank,
    )


def calc_figure_size(config: ConfigBoard) -> Tuple[int, int]:
    """
    画像のサイズを返す
    """
    return (
        config.board_width + config.x0_offset + config.x1_offset,
        config.board_height
        + config.hand_height * 2
        + config.y0_offset
        + config.y1_offset,
    )


def calc_hand_points(
    config: ConfigBoard,
) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """
    駒台の領域を返す
    """
    return (
        config.x0_offset,
        config.y0_offset,
        config.x0_offset + config.board_width,
        config.y0_offset + config.hand_height,
    ), (
        config.x0_offset,
        config.y0_offset + config.hand_height + config.board_height,
        config.x0_offset + config.board_width,
        config.y0_offset + config.hand_height * 2 + config.board_height,
    )


def board_to_png(
    board,
    config: ConfigBoard,
    move=None,
    save_png_name: str = None,
    comment: str = None,
) -> Image:
    """
    盤面をpngに変換する
    """

    im = Image.new("RGB", calc_figure_size(config), config.bg_color)

    # 将棋盤を貼る
    draw = ImageDraw.Draw(im)
    draw.font = PIL.ImageFont.truetype(config.font_path, config.font_size)

    c_image = Image.open(config.board)
    im.paste(c_image, calc_board_xy(config))

    # 駒台の領域を塗りつぶす
    hand_white, hand_black = calc_hand_points(config)
    draw.rectangle(hand_white, fill=(0, 192, 192), outline=(255, 255, 255))
    draw.rectangle(hand_black, fill=(0, 192, 192), outline=(255, 255, 255))

    # moveが非Noneの場合、moveのtoに相当する部分を塗る
    if move:
        try:
            mov_shogi = shogi.Move.from_usi(move)
            sq_to = mov_shogi.to_square
            sq_from = mov_shogi.from_square
            # print(sq_to, sq_from)
        except Exception:
            print("warning invalid move", move)
            sq_to = None
            sq_from = None

    for sq in SQUARES:

        p = board.piece_at(sq)

        rank = int(sq) // 9
        row = int(sq) % 9

        komaxy = calc_koma_xy(config, rank, row)
        if move and sq_to == sq:
            draw.rectangle(
                (
                    komaxy,
                    komaxy[0] + config.piece_width,
                    komaxy[1] + config.piece_height,
                ),
                fill=(0, 192, 192),
                outline=(0, 0, 0),
            )

        if move and sq_from == sq:
            draw.rectangle(
                (
                    komaxy,
                    komaxy[0] + config.piece_width,
                    komaxy[1] + config.piece_height,
                ),
                fill=(0, 192, 192),
                outline=(0, 0, 0),
            )

        if p is None:
            continue

        idx = p.piece_type - 1
        if p.color == Consts.WHITE:
            idx = idx + 14
        fig_name = get_koma_str(config, idx)

        c_image = Image.open(Path(fig_name))
        if p.color == Consts.WHITE:
            c_image = ImageOps.flip(ImageOps.mirror(c_image))
        im.paste(c_image, komaxy, mask=c_image)

    # 持ち駒の描画
    idx = 0
    hands = sorted(board.pieces_in_hand[Consts.BLACK], reverse=True)
    for piece_key in hands:
        piece_num = board.pieces_in_hand[Consts.BLACK][piece_key]
        if piece_num == 0:
            continue
        file_name = get_koma_str(config, piece_key - 1)
        c_image = Image.open(Path(file_name))
        hp = (hand_black[0] + idx * config.piece_width, hand_black[1])
        im.paste(c_image, hp, mask=c_image)
        if piece_num > 1:
            draw.text(
                (hp[0] + config.font_x_margin, hp[1] + config.font_y_margin),
                str(piece_num),
                (0, 0, 0),
            )
        idx += 1

    idx = 0
    hands = sorted(board.pieces_in_hand[Consts.WHITE], reverse=True)
    for piece_key in hands:
        piece_num = board.pieces_in_hand[Consts.WHITE][piece_key]
        if piece_num == 0:
            continue
        file_name = get_koma_str(config, piece_key - 1)
        c_image = Image.open(Path(file_name))
        c_image = ImageOps.flip(ImageOps.mirror(c_image))
        hp = (hand_white[2] - (idx + 1) * config.piece_width, hand_white[1])
        im.paste(c_image, hp, mask=c_image)
        if piece_num > 1:
            draw.text(
                (
                    hp[0] + config.piece_width - config.font_size,
                    hp[1]
                    + config.piece_height
                    - config.font_size
                    - config.font_y_margin,
                ),
                str(piece_num),
                (0, 0, 0),
            )
        idx += 1

    if comment:
        comment = "\n".join(textwrap.wrap(comment, config.text_width))
        draw.text(
            (
                config.x0_offset,
                config.y0_offset + config.board_height + config.hand_height * 2,
            ),
            comment,
            (0, 0, 0),
        )

    if save_png_name is not None:
        im.save(save_png_name, quality=95)
    return im


def kif_to_png(kif_file, output_dir):
    import os

    import shogi
    from shogi import KIF

    os.makedirs(output_dir, exist_ok=True)
    kif_dat = KIF.Parser.parse_file(kif_file)[0]
    board = Board()
    config = ConfigBoard()
    board_to_png(board, config, save_png_name=f"{output_dir}/{0:3}.png")
    for i, mv in enumerate(kif_dat["moves"]):
        board.push(shogi.Move.from_usi(mv))
        board_to_png(board, config, save_png_name=f"{output_dir}/{i+1:3}.png")


if __name__ == "__main__":
    board = Board(
        "l6+P1/3g1S2P/2ns1p2l/p1pkp1+b2/2n6/PrP1G2+R1/1PNp1PB2/2K6/Lg1G5 w 1S1N3P1s1l4p 118"
    )
    config = ConfigBoard()
    board_to_png(
        board,
        config,
        save_png_name="test.png",
        move="B*3g",
        comment="14時46分、藤井は約１時間近い長考で７筋の歩を突いた。\n☖７五歩までの消費時間は☗豊島１時間58分、☖藤井２時間８分。\n「普通の人なら第一感、そこに手がいきますよね」（脇九段）\n取れば☖７七歩の攻めが生じ、放置しても☖７六歩の取り込みが厳しくなる、いわゆる「筋」の一手だ。\n時刻は15時を回り、それぞれの控室に午後のおやつが用意された。\nおやつは、豊島が「レアチーズケーキ山口県産ブルーベリーソース」とブルーベリージュース、藤井が「和栗のモンブラン」とアイスレモンティー。豊島のブルーベリージュースのみ、直接対局室に運ばれている。\n現在、控室には大橋六段が解説会場から戻っており、（１）☗７五同歩には☖９四歩☗同歩☖４五銀直☗同銀☖７六桂という順を示した。\n（２）☗３三歩なら☖同桂☗同桂成☖同銀☗５五銀直☖７六歩が予想される進行。ただし、（３）☗２二歩と打ち、そこで後手も☖３三桂と跳ねるしかないなら（２）☗３三歩よりも得だという。\n考慮が40分を超えた。豊島は姿勢を正し、顔を上げ、斜め上方向に視線を飛ばす。",
    )
