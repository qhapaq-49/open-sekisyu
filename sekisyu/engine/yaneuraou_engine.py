from sekisyu.engine.base_engine import BaseEngine, Turn


class YaneuraOuEngine(BaseEngine):
    """
    やねうら王のクラス

    USIプロトコルを介し、対局や各種局面の解析を行う。
    特定のエンジンにしか無い機能はここに適宜書いていく
    """

    def get_moves(self) -> str:
        """
        [SYNC] usi_position()で設定した局面に対する合法手の指し手の集合を得る。
        USIプロトコルでの表記文字列で返ってくる。
        すぐに返ってくるはずなのでブロッキングメソッド
        "moves"は、やねうら王でしか使えないUSI拡張コマンド
        """
        return self.send_command_and_getline("moves")

    def get_side_to_move(self) -> Turn:
        """
        [SYNC] usi_position()で設定した局面に対する手番を得る。
        "side"は、やねうら王でしか使えないUSI拡張コマンド
        """
        line = self.send_command_and_getline("side")
        return Turn.BLACK if line == "black" else Turn.WHITE
