from sekisyu.ensemble.base_ensembler import BaseEnsembler
from sekisyu.playout.playinfo import BasePlayInfoPack
from typing import List
from dacite import from_dict
import copy
import dataclasses

class YaneDLEnsembler(BaseEnsembler):
    def __init__(self, bonus_ratio):
        self.bonus_ratio = bonus_ratio
        
    def ensemble(self, playinfos:List[BasePlayInfoPack], pos:str) -> BasePlayInfoPack:
        # 出力はensembleの結果、やねの結果、dlの結果の順番にする
        # idx 0 がdl、idx 1がやね! ホントはこれもassertしたい
        assert len(playinfos) == 2, f"invalid number of playinfos. detected={len(playinfos)}, expected=2"
        yane_bestmove = playinfos[1].infos[0].pv[0]
        yane_nodes = playinfos[1].infos[0].nodes
        node_best = playinfos[0].infos[0].nodes
        
        output = from_dict(data_class=BasePlayInfoPack, data=dataclasses.asdict(playinfos[0]))
        best = playinfos[0].infos[0]
        bm_change = False 
        not_in_pv = True
        for info in playinfos[0].infos:
            if info.pv[0] == yane_bestmove:
                not_in_pv = False
                info.nodes += yane_nodes * self.bonus_ratio
                # 本当は出力を凝るべきだが面倒なのでやらない
                if info.nodes > node_best:
                    best = info
                    bm_change = True
                break
        if not_in_pv and yane_nodes * self.bonus_ratio > node_best:
            best = playinfos[1].infos[0]
            bm_change = True
        # debug
        #if not bm_change:
        #    print("yane_info", yane_bestmove, "dlinfo", playinfos[0].infos[0].pv[0], "ensemble", best.pv[0], "yane_nodes", yane_nodes, "bm_change", bm_change, "notinpv", not_in_pv)
                    
        output.infos = [best]
        output.infos.extend(playinfos[1].infos)
        output.infos.extend(playinfos[0].infos)
        return output
    
class YaneDLEnsemblerPositive(BaseEnsembler):
    """
    楽観合議をするアンサンブラー。純粋な評価値でやると色々齟齬がありそうなので
    nodesに応じてボーナスをつける形式にする。合議の種類をいろいろ試して強いのを使いたい
    """
    def __init__(self, bonus_ratio_a, bonus_ratio_b):
        # やねとdlのnodes比率がxxに対して線形にボーナスを乗っける
        # bonus = bonus_ratio_a * X + b
        self.bonus_ratio_a = bonus_ratio_a
        self.bonus_ratio_b = bonus_ratio_b
        
    def ensemble(self, playinfos:List[BasePlayInfoPack], pos:str) -> BasePlayInfoPack:
        # 出力はensembleの結果、やねの結果、dlの結果の順番にする
        # idx 0 がdl、idx 1がやね! ホントはこれもassertしたい
        assert len(playinfos) == 2, f"invalid number of playinfos. detected={len(playinfos)}, expected=2"
        output = from_dict(data_class=BasePlayInfoPack, data=dataclasses.asdict(playinfos[0]))
        dl_value = playinfos[0].infos[0].eval
        yane_value = playinfos[1].infos[0].eval
        yane_nodes = playinfos[1].infos[0].nodes
        dl_nodes = playinfos[0].infos[0].nodes # dlshogi側のnodesは全探索数ではなくbestmoveのnodesでいいのか？
        yane_eval_positive = yane_value + self.bonus_ratio_a * yane_nodes / dl_nodes + self.bonus_ratio_b
        if yane_eval_positive > dl_value:
            output.infos = [playinfos[1].infos[0]]
            output.infos.extend(playinfos[0].infos)
        else:
            output.infos = [playinfos[0].infos[0]]
            output.infos.append(playinfos[1].infos)
        
        return output
