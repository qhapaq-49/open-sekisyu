from typing import List


# 文字列のparseを行うもの。
class Scanner:

    # argsとしてstr[]を渡しておく。
    # args[index]のところからスキャンしていく。
    def __init__(self, args: [], index: int = 0):
        self.__args = args
        self.__index = index

    # 次のtokenを覗き見する。tokenがなければNoneが返る。
    # indexは進めない
    def peek_token(self) -> str:
        if self.is_eof():
            return None
        return self.__args[self.__index]

    # 次のtokenを取得して文字列として返す。indexを1進める。
    def get_token(self) -> str:
        if self.is_eof():
            return None
        token = self.__args[self.__index]
        self.__index += 1
        return token

    # 次のtokenを取得して数値化して返す。indexを1進める。
    def get_integer(self) -> int:
        if self.is_eof():
            return None
        token = self.__args[self.__index]
        self.__index += 1
        try:
            return int(token)
        except ValueError:
            return None

    # indexが配列の末尾まで行ってればtrueが返る。
    def is_eof(self) -> bool:
        return len(self.__args) <= self.__index

    # index以降の文字列を連結して返す。
    # indexは配列末尾を指すようになる。(is_eof()==Trueを返すようになる)
    def rest_string(self) -> str:
        rest = " ".join(self.__args[self.__index :])
        self.__index = len(self.__args)
        return rest

    def rest_string_list(self) -> List[str]:
        rest = self.__args[self.__index :]
        self.__index = len(self.__args)
        return rest

    # 元の配列をスペースで連結したものを返す。
    def get_original_text(self) -> str:
        return " ".join(self.__args)
