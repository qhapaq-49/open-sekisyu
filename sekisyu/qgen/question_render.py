import dataclasses
import random

import PIL
import shogi
from PIL import ImageDraw
from sekisyu.board.board_to_png_l2 import ConfigBoard, board_to_png
from sekisyu.board.get_board_from_pos_cmd import get_board_from_pos_cmd
from sekisyu.kif_ja.kif_ja_parser import translate_pv
from sekisyu.qgen.next_ply_question import NextPlyQuestion


@dataclasses.dataclass
class ConfigQuestionRender:
    config_board: ConfigBoard = ConfigBoard()
    use_before_pos: bool = False
    selection: int = 5
    print_answer: bool = True
    print_selection: bool = True


def question_render(
    question: NextPlyQuestion, config: ConfigQuestionRender, qname: str
):
    board = get_board_from_pos_cmd(question.question_pos)
    img = board_to_png(board, config.config_board)
    # font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(img)
    font_ttf = "/usr/share/fonts/OTF/TakaoPMincho.ttf"
    draw.font = PIL.ImageFont.truetype(font_ttf, 20)
    teban_str = "先手" if board.turn == shogi.BLACK else "後手"
    selection_txt = f"次の一手は？ ({teban_str}) \n"
    sel_num = min(config.selection, len(question.playinfo.infos))
    alias = [i for i in range(sel_num)]
    if not config.print_answer:
        random.shuffle(alias)
    if config.print_selection:
        for i in range(sel_num):
            # ans = translate_pv(question.current_pos, [info.pv[0]], question.before_pv[-1] if len(question.before_pv) > 0 else None)
            ans = translate_pv(
                question.question_pos, [question.playinfo.infos[alias[i]].pv[0]]
            )
            if config.print_answer:
                selection_txt += f"  {str(i+1)}. {ans} 評価値 {question.playinfo.infos[alias[i]].eval}\n"
                selection_txt += (
                    translate_pv(
                        question.question_pos, question.playinfo.infos[alias[i]].pv
                    )
                    + "\n"
                )
            else:
                selection_txt += f"  {str(i+1)}. {ans}\n"
    draw.text(
        (
            config.config_board.x0_offset,
            config.config_board.y0_offset
            + config.config_board.board_height
            + config.config_board.hand_height * 2,
        ),
        selection_txt,
        (0, 0, 0),
    )

    # if config.print_answer:
    #    answer_txt =

    img.save(qname)


if __name__ == "__main__":
    import json

    from dacite import Config, from_dict

    with open("assets/ques/test_ques.json") as f:
        dat = json.load(f)
    ques = from_dict(
        data_class=NextPlyQuestion, data=dat, config=Config(cast=[tuple, int, str])
    )
    config = ConfigQuestionRender(config_board=ConfigBoard())
    question_render(ques, config, "out.png")
