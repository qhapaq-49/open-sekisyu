import dataclasses
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageOps
from shogi import SQUARES, Board, Consts


@dataclasses.dataclass
class ConfigBoard:
    """
    盤面描画用のconfig
    """

    # 将棋盤の画像
    board: str = "assets/visualize/board/board.jpg"

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

    # ボードの外の横幅（駒台とアバターの横幅）
    side_width: int = 250

    # 駒台、アバターと盤面のマージン
    side_margin: int = 10

    # アバターの縦横幅
    avater_width: int = 250
    avater_height: int = 280

    # アバターと駒台のy方向のマージン
    avater_margin_y: int = 20

    # 駒同士のマージン
    hand_margin_y: int = 5
    hand_margin_x: int = 5

    # バックグラウンドの色
    bg_color: Tuple[int, int, int] = (255, 255, 255)
    hand_color: Tuple[int, int, int] = (128, 128, 128)


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
    return config.side_width + config.side_margin, 0


def calc_koma_xy(config: ConfigBoard, rank: int, row: int) -> Tuple[int, int]:
    board_x, board_y = calc_board_xy(config)
    return (
        board_x + config.piece_offset_x + config.piece_x * row,
        board_y + config.piece_offset_y + config.piece_y * rank,
    )


def calc_figure_size(config: ConfigBoard) -> Tuple[int, int]:
    return (
        config.board_width + (config.side_width + config.side_margin) * 2,
        config.board_height,
    )


def calc_margin_2p(config: ConfigBoard) -> int:
    return config.board_width + config.side_width + config.side_margin * 2


def calc_hand_points(
    config: ConfigBoard,
) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    return (
        0,
        0,
        config.side_width,
        config.board_height - config.avater_height - config.avater_margin_y,
    ), (
        calc_margin_2p(config),
        config.avater_height + config.avater_margin_y,
        calc_margin_2p(config) + config.side_width,
        config.board_height,
    )


def calc_hand_piece_points_black(
    config: ConfigBoard, idx: int, p: int, is_pawn: bool
) -> List[Tuple[int, int]]:
    row = idx // 2
    col = idx % 2
    _, black = calc_hand_points(config)
    if is_pawn:
        if col == 1:
            row += 1
            col = 0
        piece_width = config.side_width - config.hand_margin_x * 2
    else:
        piece_width = int(config.side_width / 2 - config.hand_margin_x * 1.5)

    piece_x_inc = int((piece_width - config.piece_width) / max(1, p - 1))
    x_point = (
        black[0] + config.hand_margin_x + (config.hand_margin_x + piece_width) * col
    )
    y_point = (
        black[1]
        + config.hand_margin_y
        + row * (config.piece_height + config.hand_margin_y)
    )

    return [(x_point + piece_x_inc * (p - 1 - i), y_point) for i in range(p)]


def calc_hand_piece_points_white(
    config: ConfigBoard, idx: int, p: int, is_pawn: bool
) -> List[Tuple[int, int]]:
    row = idx // 2
    col = idx % 2
    white, _ = calc_hand_points(config)
    if is_pawn:
        if col == 1:
            row += 1
            col = 0
        piece_width = config.side_width - config.hand_margin_x * 2
    else:
        piece_width = int(config.side_width / 2 - config.hand_margin_x * 1.5)

    piece_x_inc = int((piece_width - config.piece_width) / max(1, p - 1))
    x_point = (
        white[2]
        - config.piece_width
        - config.hand_margin_x
        - (config.hand_margin_x + piece_width) * col
    )
    y_point = (
        white[3]
        - config.piece_height
        - config.hand_margin_y
        - row * (config.piece_height + config.hand_margin_y)
    )

    return [(x_point - piece_x_inc * (p - 1 - i), y_point) for i in range(p)]


def calc_hand_point_white(config: ConfigBoard) -> Tuple[int, int]:
    return 0, 0


def board_to_png(
    board, config: ConfigBoard, move=None, save_png_name: str = None
) -> None:
    """
    盤面をpngに変換する
    """

    im = Image.new("RGB", calc_figure_size(config), config.bg_color)
    draw = ImageDraw.Draw(im)
    c_image = Image.open(config.board)
    im.paste(c_image, calc_board_xy(config))
    hand1p, hand2p = calc_hand_points(config)
    draw.rectangle(hand1p, fill=(0, 192, 192), outline=(255, 255, 255))
    draw.rectangle(hand2p, fill=(0, 192, 192), outline=(255, 255, 255))
    for sq in SQUARES:
        p = board.piece_at(sq)
        if p is None:
            continue
        idx = p.piece_type - 1
        if p.color == Consts.WHITE:
            idx = idx + 14
        fig_name = get_koma_str(config, idx)
        rank = int(sq) // 9
        row = int(sq) % 9
        c_image = Image.open(Path(fig_name))
        if p.color == Consts.WHITE:
            c_image = ImageOps.flip(ImageOps.mirror(c_image))
        im.paste(c_image, calc_koma_xy(config, rank, row), mask=c_image)

    # 持ち駒の描画
    idx = 0
    hands = sorted(board.pieces_in_hand[Consts.BLACK], reverse=True)
    for piece_key in hands:
        piece_num = board.pieces_in_hand[Consts.BLACK][piece_key]
        file_name = get_koma_str(config, piece_key - 1)
        c_image = Image.open(Path(file_name))
        hand_piece = calc_hand_piece_points_black(
            config, idx, piece_num, piece_key == 1
        )
        for hp in hand_piece:
            im.paste(c_image, hp, mask=c_image)
        idx += 1

    idx = 0
    hands = sorted(board.pieces_in_hand[Consts.WHITE], reverse=True)
    for piece_key in hands:
        piece_num = board.pieces_in_hand[Consts.WHITE][piece_key]
        file_name = get_koma_str(config, piece_key - 1)
        c_image = Image.open(Path(file_name))
        c_image = ImageOps.flip(ImageOps.mirror(c_image))
        hand_piece = calc_hand_piece_points_white(
            config, idx, piece_num, piece_key == 1
        )
        for hp in hand_piece:
            im.paste(c_image, hp, mask=c_image)
        idx += 1

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
    board = Board()
    config = ConfigBoard()
    board_to_png(board, config, save_png_name="test.png")
