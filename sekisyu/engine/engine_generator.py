from typing import Dict, Any
from sekisyu.engine.base_engine import BaseEngine, UsiEngineState
from sekisyu.engine.config_engine import ConfigEngine
from sekisyu.engine.virtual_engine.forcebook_engine import ForceBookEngine
from sekisyu.engine.yaneuraou_engine import YaneuraOuEngine
from sekisyu.engine.dlshogi_engine import DlshogiEngine
from sekisyu.engine.virtual_engine.ensemble_engine import EnsembleEngine
from sekisyu.ensemble.ensemble_generator import generate_ensembler_dict


def generate_engine_dict(config:Dict[str, Any]) -> BaseEngine:
    """
    エンジンの生成 from dict
    configを使ったやつが拡張性が低くて困るのでこっちに移行する


    Args:
        config (dict(str, any)): エンジンの条件
        wait_for_readyok (bool) : readyokが出るまで待つ

    Returns:
        BaseEngine : エンジン
    """
    if config["engine_mode"] == "yaneuraou":
        engine = YaneuraOuEngine(config["engine_name"])
        engine.set_option(config["option"])
        engine.boot(config["engine_path"])
    elif config["engine_mode"] == "dlshogi":
        engine = DlshogiEngine(config["engine_name"])
        engine.set_option(config["option"])
        engine.boot(config["engine_path"])
    
    elif config["engine_mode"] == "forcebook":
        base_engine = generate_engine_dict(config["base_engine_config"])
        engine = ForceBookEngine(base_engine, config["engine_name"], config["engine_config"])     
    elif config["engine_mode"] == "ensemble":
        engines = []
        for base in config["base_engine_configs"]:
            engines.append(generate_engine_dict(base))
        ensembler = generate_ensembler_dict(config["ensembler_config"])
        engine = EnsembleEngine(engines, ensembler, config["engine_name"])
        
    else:
        engine = BaseEngine(config["engine_name"])
        engine.set_option(config["option"])
        engine.boot(config["engine_path"])
    
    engine.wait_for_state(UsiEngineState.WaitCommand)
    return engine
