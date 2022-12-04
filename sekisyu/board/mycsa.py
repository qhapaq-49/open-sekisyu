# -*- coding: utf-8 -*-
#
# This file is part of the python-shogi library.
# Copyright (C) 2015- Tasuku SUENAGA <tasuku-s-github@titech.ac>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re

import shogi
from shogi.CSA import COLOR_SYMBOLS, Exporter
from shogi.CSA import Parser as ParserShogi


class Parser(ParserShogi):  # type:ignore
    @staticmethod
    def parse_file(path):
        with open(path) as f:
            return Parser.parse_str(f.read())

    @staticmethod
    def parse_comment(comment, sfen):
        board = shogi.Board(sfen)
        # parse comment to get pv and value
        m = re.match(r"'\*\*\s(\-?[\d]+)\s?(.*)", comment)
        # m is pv and value
        if m is not None:
            value = m.groups()[0]
            move_csa_list = m.groups()[1].split(" ")
            move_str_list = []
            for move_csa in move_csa_list:
                if move_csa == "":
                    continue
                (color, move) = Parser.parse_move_str(move_csa, board)
                board.push(shogi.Move.from_usi(move))
                move_str_list.append(move)
            return int(value), move_str_list, None
        else:
            return None, None, comment

    @staticmethod
    def parse_str(csa_str):
        line_no = 1

        sfen = None
        board = None
        position_lines = []
        names = [None, None]
        current_turn_str = None
        moves = []
        lose_color = None
        move_start = False
        values = []
        pvs = []
        comments = []
        temp_values = []
        temp_pvs = []
        temp_comments = []

        for line in csa_str.split("\n"):
            if line == "":
                pass
            elif line[0] == "'":
                if move_start:
                    try:
                        value, pv, comment = Parser.parse_comment(line, board.sfen())
                        if value is not None:
                            temp_values.append(value)
                        if pv is not None:
                            temp_pvs.append(pv)
                        if comment is not None:
                            temp_comments.append(comment)
                    except Exception:
                        # skip the invalid comments
                        pass

            elif line[0] == "V":
                # Currently just ignoring version
                pass
            elif line[0] == "N" and line[1] in COLOR_SYMBOLS:
                names[COLOR_SYMBOLS.index(line[1])] = line[2:]
            elif line[0] == "$":
                # Currently just ignoring information
                pass
            elif line[0] == "P":
                position_lines.append(line)
            elif line[0] in COLOR_SYMBOLS:
                if len(line) == 1:
                    current_turn_str = line[0]
                else:
                    if not board:
                        raise ValueError(
                            "Board infomation is not defined before a move"
                        )
                    (color, move) = Parser.parse_move_str(line, board)
                    moves.append(move)
                    board.push(shogi.Move.from_usi(move))
                    move_start = True
                    pvs.append([v for v in temp_pvs])
                    values.append([v for v in temp_values])
                    comments.append([v for v in temp_comments])
                    temp_pvs = []
                    temp_values = []
                    temp_comments = []
            elif line[0] == "T":
                # Currently just ignoring consumed time
                pass
            elif line[0] == "%":
                # End of the game
                if not board:
                    raise ValueError(
                        "Board infomation is not defined before a special move"
                    )
                if line in ["%TORYO", "%TIME_UP", "%ILLEGAL_MOVE"]:
                    lose_color = board.turn
                elif line == "%+ILLEGAL_ACTION":
                    lose_color = shogi.BLACK
                elif line == "%-ILLEGAL_ACTION":
                    lose_color = shogi.WHITE
                pvs.append([v for v in temp_pvs])
                values.append([v for v in temp_values])
                comments.append([v for v in temp_comments])

                # TODO: Support %MATTA etc.
                break
            elif line == "/":
                raise ValueError("Dont support multiple matches in str")
            else:
                raise ValueError("Invalid line {0}: {1}".format(line_no, line))
            if board is None and current_turn_str:
                position = Parser.parse_position(position_lines)
                sfen = Exporter.sfen(
                    position["pieces"], position["pieces_in_hand"], current_turn_str, 1
                )
                board = shogi.Board(sfen)
            line_no += 1

        if lose_color == shogi.BLACK:
            win = "w"
        elif lose_color == shogi.WHITE:
            win = "b"
        else:
            win = "-"

        summary = {
            "names": names,
            "sfen": sfen,
            "moves": moves,
            "win": win,
            "values": values[1:],
            "pvs": pvs[1:],
            "comments": comments[1:],
        }
        # NOTE: for future support of multiple matches
        return [summary]
