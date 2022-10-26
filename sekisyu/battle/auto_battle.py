import os

from sekisyu.battle.battle_server import BattleServer
from sekisyu.battle.config_auto_battle import AutoBattleResult, ConfigAutoBattle
from sekisyu.csa.csa import playout_to_csa_v22
from sekisyu.engine.engine_generator import generate_engine_dict


def kif_make(conf: ConfigAutoBattle, reboot_engine: bool = False) -> AutoBattleResult:
    print(conf)
    engine1 = generate_engine_dict(conf.config_1p)
    engine2 = generate_engine_dict(conf.config_2p)
    engine1.set_print_info(False)
    engine2.set_print_info(False)
    server: BattleServer = BattleServer(engine1, engine2, conf.config)

    os.makedirs(os.path.dirname(conf.kif_prefix), exist_ok=True)

    win_1p_black: int = 0
    win_1p_white: int = 0
    draw_1p_black: int = 0
    draw_1p_white: int = 0

    win_2p_black: int = 0
    win_2p_white: int = 0
    draw_2p_black: int = 0
    draw_2p_white: int = 0

    for i in range(conf.battle_num):
        if conf.flip:
            if i % 2 == 1:
                server.is_2p_black = True
            else:
                server.is_2p_black = False
        playout = server.play_one_game()

        if playout.result.is_black_win():
            if server.is_2p_black:
                win_2p_black += 1
            else:
                win_1p_black += 1
        if playout.result.is_white_win():
            if server.is_2p_black:
                win_1p_white += 1
            else:
                win_2p_white += 1
        if playout.result.is_draw():
            if server.is_2p_black:
                draw_1p_white += 1
                draw_2p_black += 1
            else:
                draw_2p_white += 1
                draw_1p_black += 1

        if i % conf.print_interval == 0:
            print(
                f"{win_1p_black+win_1p_white}-{draw_1p_black+draw_1p_white}-{win_2p_black+win_2p_white} 1p_black {win_1p_black} - {draw_1p_black} - {win_2p_white}, 1p_white {win_1p_white} - {draw_1p_white} - {win_2p_black}"  # noqa
            )
        if server.is_2p_black:
            if conf.save_json:
                playout.to_json(
                    f"{conf.kif_prefix}{playout.timestamp}_{engine2.engine_name}_{engine1.engine_name}_{i}.json"
                )
            if conf.save_csa:
                playout_to_csa_v22(
                    playout,
                    f"{conf.kif_prefix}{playout.timestamp}_{engine2.engine_name}_{engine1.engine_name}_{i}.csa",
                )
        else:
            if conf.save_json:
                playout.to_json(
                    f"{conf.kif_prefix}{playout.timestamp}_{engine1.engine_name}_{engine2.engine_name}_{i}.json"
                )
            if conf.save_csa:
                playout_to_csa_v22(
                    playout,
                    f"{conf.kif_prefix}{playout.timestamp}_{engine1.engine_name}_{engine2.engine_name}_{i}.csa",
                )
        if reboot_engine:
            server.terminate()
            engine1 = generate_engine(conf.config_1p)
            engine2 = generate_engine(conf.config_2p)
            server: BattleServer = BattleServer(engine1, engine2, conf.config)

    server.terminate()
    return AutoBattleResult(
        win_1p_black=win_1p_black,
        win_1p_white=win_1p_white,
        draw_1p_black=draw_1p_black,
        draw_1p_white=draw_1p_white,
        win_2p_black=win_2p_black,
        win_2p_white=win_2p_white,
    )
