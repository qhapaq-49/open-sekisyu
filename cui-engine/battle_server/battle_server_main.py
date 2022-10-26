import argparse

import yaml
from dacite import Config, from_dict
from sekisyu.battle.auto_battle import kif_make
from sekisyu.battle.config_auto_battle import ConfigAutoBattle


def main():
    """
    sample usage battle_server.exe --config battle_server_example.yaml
    """
    parser = argparse.ArgumentParser(description="config of battle")
    parser.add_argument("--config", help="config files for analysis")
    args = parser.parse_args()
    with open(args.config, "r") as f:
        data = yaml.safe_load(f)
    config = from_dict(
        data_class=ConfigAutoBattle, data=data, config=Config(cast=[tuple, int, str])
    )
    kif_make(config)


if __name__ == "__main__":
    main()
