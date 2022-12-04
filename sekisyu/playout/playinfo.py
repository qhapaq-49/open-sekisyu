import copy
import dataclasses
from dataclasses import field
from typing import Dict, List, Union

from sekisyu.playout.log_scanner import Scanner
from sekisyu.playout.usi_value import UsiEvalValue


@dataclasses.dataclass
class BasePlayInfo:
    """
    各エンジンからinfoで与えられる指し手の情報

    Baseクラスでは各種GUIエンジンの出力に準拠したパラメタを扱う。個別のパラメタを作りたい場合は本クラスを継承すること

    pv (list(str)):
        読み筋のリスト。pv[0]は実際の指し手、pv[1]はponderに相当

    nps (int):
        node per second、1秒あたりに読んだ局面数。出力されないこともあるのでデフォルトで0

    nodes (int):
        nodes 読んだ局面数。出力されないこともあるのでデフォルトで0

    time (int):
        ミリ秒単位の消費時間。デフォルトは0

    depth (int):
        局面を読んだ深さ。デフォルトは0

    seldepth (int):
        選択的な深さ。デフォルトは0

    is_upperbound (bool):
        upperboundであるか。デフォルトはFalse

    is_lowerbound (bool):
        lowerboundであるか。デフォルトはFalse

    eval (UsiEvalValue):
        評価値。デフォルトは0

    hashfull (int):
        hash利用の千分率。デフォルトは0

    multipv (int):
        multipvの値。デフォルトは1
    """

    pv: List[str] = field(default_factory=list)
    nps: int = 0
    nodes: int = 0
    is_upperbound: bool = False
    is_lowerbound: bool = False
    depth: int = 0
    time: int = 0
    seldepth: int = 0
    hashfull: int = 0
    multipv: int = 1
    eval: UsiEvalValue = UsiEvalValue(0)

    def __deepcopy__(self) -> "BasePlayInfo":
        return self.copy()

    def is_mate(self) -> bool:
        """
        詰ませることが可能な局面であるか。
        playinfoは解析結果を機械的に読み出しているだけであることに注意
        """
        return UsiEvalValue(self.eval).is_mate_score()

    def is_mated(self) -> bool:
        """
        詰まされている局面であるか。
        playinfoは解析結果を機械的に読み出しているだけであることに注意
        """
        return UsiEvalValue(self.eval).is_mated_score()

    def get_usi_str(self) -> str:
        """
        usiプロトコルに従ってログを吐く
        """
        output = f"info nps {self.nps} nodes {self.nodes} score cp {self.eval} depth {self.depth} pv {' '.join(self.pv)}"
        return output

    def copy(self) -> "BasePlayInfo":
        out = BasePlayInfo()
        out.pv = copy.deepcopy(self.pv)
        out.nps = self.nps
        out.nodes = self.nodes
        out.is_lowerbound = self.is_lowerbound
        out.is_upperbound = self.is_upperbound
        out.depth = self.depth
        out.time = self.time
        out.seldepth = self.seldepth
        out.hashfull = self.hashfull
        out.multipv = self.multipv
        out.eval = self.eval
        return out

    def to_dict(self) -> Dict:
        """
        jsonでdump可能なdictを返す

        Returns:
            dict(str, any) : dict情報
        """
        return {
            "pv": self.pv,
            "nps": self.nps,
            "nodes": self.nodes,
            "is_upperbound": self.is_upperbound,
            "is_lowerbound": self.is_lowerbound,
            "depth": self.depth,
            "time": self.time,
            "seldepth": self.seldepth,
            "hashfull": self.hashfull,
            "multipv": self.multipv,
            "eval": int(self.eval),
        }


@dataclasses.dataclass
class BasePlayInfoPack:
    """
    info, bestmoveの情報を集約した局面解析の情報

    infos (list(BasePlayInfo)):
        pvのリスト。multiponderに対応してlistとする

    elapsed int:
        消費時間

    bestmove: str
        エンジンから出力された指し手

    ponder : str
        エンジンから出力された予測手
    """

    infos: List[BasePlayInfo] = field(default_factory=list)
    elapsed: int = 0
    bestmove: str = ""
    ponder: str = ""

    def __deepcopy__(self) -> "BasePlayInfoPack":
        return self.copy()

    def generate_ponder_from_pv(self) -> None:
        """
        エンジンがponderを返さなかった場合などに、infoからponderを生成する
        """
        for info in self.infos:
            if info.pv[0] == self.bestmove and len(info.pv) > 1:
                self.ponder = info.pv[1]

    def copy(self) -> "BasePlayInfoPack":
        out = BasePlayInfoPack()
        out.infos = [info.copy() for info in self.infos]
        out.elapsed = self.elapsed
        out.bestmove = self.bestmove
        out.ponder = self.ponder
        return out

    def to_dict(self) -> Dict:
        """
        jsonでdump可能なdictを返す

        Returns:
            dict(str, any) : dict情報
        """
        return {
            "bestmove": self.bestmove,
            "ponder": self.ponder,
            "infos": [info.to_dict() for info in self.infos],
        }


def generate_playinfo_from_info(message: str) -> Union[BasePlayInfo, None]:

    # 解析していく
    scanner = Scanner(message.split(), 1)
    pv = BasePlayInfo()
    while not scanner.is_eof():
        try:
            token = scanner.get_token()
            if token == "string":
                return None
            elif token == "depth":
                v = scanner.get_integer()
                if v is not None:
                    pv.depth = v
            elif token == "seldepth":
                v = scanner.get_integer()
                if v is not None:
                    pv.seldepth = v
            elif token == "nodes":
                v = scanner.get_integer()
                if v is not None:
                    pv.nodes = v
            elif token == "nps":
                v = scanner.get_integer()
                if v is not None:
                    pv.nps = v
            elif token == "hashfull":
                v = scanner.get_integer()
                if v is not None:
                    pv.hashfull = v
            elif token == "time":
                v_str = scanner.get_token()
                if v_str is not None:
                    pv.time = int(v_str)
            elif token == "pv":
                pv.pv = scanner.rest_string_list()
            elif token == "multipv":
                v = scanner.get_integer()
                if v is not None:
                    pv.multipv = v
            # 評価値絡み
            elif token == "score":
                token = scanner.get_token()
                if token == "mate":
                    bw_token = scanner.peek_token()
                    if bw_token is not None:
                        is_minus = bw_token[0] == "-"
                        try:
                            v = scanner.get_integer()
                            ply = int(
                                v if v is not None else 3
                            )  # pylintが警告を出すのでintと明示しておく。
                        except Exception:
                            ply = (
                                3  # if no ply info is given assume this is checkmate+1
                            )
                        if not is_minus:
                            pv.eval = UsiEvalValue.mate_in_ply(ply)
                        else:
                            pv.eval = UsiEvalValue.mated_in_ply(-ply)
                elif token == "cp":
                    v = scanner.get_integer()
                    if v is not None:
                        pv.eval = UsiEvalValue(v)

                # この直後に"upperbound"/"lowerbound"が付与されている可能性がある。
                token = scanner.peek_token()
                if token == "upperbound":
                    pv.is_upperbound = True
                    pv.is_lowerbound = False
                    scanner.get_token()
                elif token == "lowerbound":
                    pv.is_lowerbound = True
                    pv.is_upperbound = False
                    scanner.get_token()
                else:
                    pv.is_lowerbound = False
                    pv.is_upperbound = False

            # "info string.."はコメントなのでこの行は丸ごと無視する。
            else:
                raise ValueError(f"ParseError {token}")
        except Exception:
            raise ValueError
    # pv check
    # やねうら王の場合、定跡にあたると文字列に%が含まれてしまうのでソイツを削る
    if "%" in pv.pv[-1]:
        pv.pv = pv.pv[:-1]
    return pv
