from sekisyu.ensemble.base_ensembler import BaseEnsembler
from sekisyu.playout.playinfo import BasePlayInfoPack
from typing import List, Optional, Tuple
from dacite import from_dict
import copy
import dataclasses

class PositiveEnsembler(BaseEnsembler):
    """
    シンプルな楽観合議
    """
    def __init__(self, bonus: Optional[List[int]]=None, bonus_by_ply: Optional[int]=None, bonus_by_eval :List[Tuple[int, int]]=None, book_th:Optional[int]=None) ->None:
        self.bonus = bonus
        self.bonus_by_ply = bonus_by_ply
        self.bonus_by_eval = bonus_by_eval
        self.book_th = book_th
        
    def ensemble(self, playinfos:List[BasePlayInfoPack], pos:str) -> BasePlayInfoPack:
        vmax = -9999999
        max_idx = -1
        ply = 0
        if "moves" in pos:
            ply = len(pos.split(" ")) - 2
    
        for i, infos in enumerate(playinfos):

            # 何らかの事情でクラッシュしてる
            if len(infos.infos) == 0:
                continue
            v = infos.infos[0].eval
            if i == 0 and infos.infos[0].eval > 30000 or infos.infos[0].eval < -30000:
                v += 99999
            # 定跡の処理。nodeの数でhookするというhackyな仕様
            if i == 0 and self.book_th is not None and infos.infos[0].nodes < self.book_th:
                v += 99999

            if self.bonus_by_eval:
                if self.bonus_by_eval[i][0] < v:
                    v += self.bonus_by_eval[i][1]
            if self.bonus:
                v += self.bonus[i]
            if self.bonus_by_ply:
                v += ply * self.bonus_by_ply[i]
            print("info string score", v, "nodes ", infos.infos[0].nodes, infos.infos[0].pv[0])
            if v > vmax:
                vmax = v
                max_idx = i
        # TODO : もうちょっとちゃんとログを集めるとかしたい
        return playinfos[max_idx]
