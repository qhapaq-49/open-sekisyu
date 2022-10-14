from sekisyu.playout.playinfo import BasePlayInfoPack
from typing import List

class BaseEnsembler:
    def __init__(self):
        pass
    
    def ensemble(self, playinfos:List[BasePlayInfoPack], pos:str) -> BasePlayInfoPack:
        raise NotImplementedError