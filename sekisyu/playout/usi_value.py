from enum import Enum, IntEnum


# 特殊な評価値(Eval)を表現するenum
class UsiEvalSpecialValue(IntEnum):

    # 0手詰めのスコア(rootで詰んでいるときのscore)
    # 例えば、3手詰めならこの値より3少ない。
    ValueMate = 100000

    # MaxPly(256)手で詰むときのスコア
    ValueMateInMaxPly = ValueMate - 256

    # 詰まされるスコア
    ValueMated = -int(ValueMate)

    # MaxPly(256)手で詰まされるときのスコア
    ValueMatedInMaxPly = -int(ValueMateInMaxPly)

    # Valueの取りうる最大値(最小値はこの符号を反転させた値)
    ValueInfinite = 100001

    # 無効な値
    ValueNone = 100002


# 評価値(Eval)を表現する型
class UsiEvalValue(int):

    # 詰みのスコアであるか
    def is_mate_score(self):
        return (
            UsiEvalSpecialValue.ValueMateInMaxPly <= self
            and self <= UsiEvalSpecialValue.ValueMate
        )

    # 詰まされるスコアであるか
    def is_mated_score(self):
        return (
            UsiEvalSpecialValue.ValueMated <= self
            and self <= UsiEvalSpecialValue.ValueMatedInMaxPly
        )

    # 評価値を文字列化する。
    def to_string(self):
        if self.is_mate_score():
            return "mate " + str(UsiEvalSpecialValue.ValueMate - self)
        elif self.is_mated_score():
            # マイナスの値で表現する。self == UsiEvalSpecialValue.ValueMated のときは -0と表現する。
            return "mate -" + str(self - UsiEvalSpecialValue.ValueMated)
        return "cp " + str(self)

    # ply手詰みのスコアを数値化する
    # UsiEvalValueを返したいが、このクラスの定義のなかでは自分の型を明示的に返せないようで..(コンパイラのバグでは..)
    # ply : integer
    @staticmethod
    def mate_in_ply(ply: int):  # -> UsiEvalValue
        return UsiEvalValue(int(UsiEvalSpecialValue.ValueMate) - ply)

    # ply手で詰まされるスコアを数値化する
    # ply : integer
    @staticmethod
    def mated_in_ply(ply: int):  # -> UsiEvalValue:
        return UsiEvalValue(-int(UsiEvalSpecialValue.ValueMate) + ply)


# 読み筋として返ってきた評価値がfail low/highしたときのスコアであるか
class UsiBound(Enum):
    BoundNone = 0
    BoundUpper = 1
    BoundLower = 2
    BoundExact = 3

    # USIプロトコルで使う文字列化して返す。
    def to_string(self) -> str:
        if self == self.BoundUpper:
            return "upperbound"
        elif self == self.BoundLower:
            return "lowerbound"
        return ""
