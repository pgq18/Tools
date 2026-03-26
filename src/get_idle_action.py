#!/usr/bin/env python
"""获取 bi_alicia_d 机械臂的 idle_action 值

使用方法:
1. 运行脚本
2. 手动将机械臂移动到期望的空闲位置
3. 从输出中复制状态值作为 idle_action
"""

import time
from lerobot.robots import make_robot_from_config
from lerobot.robots.bi_alicia_d_follower.config_bi_alicia_d_follower import BiAliciaDFollowerConfig

def main():
    # 配置机械臂 (参考 record_dual_arms.sh 的配置)
    config = BiAliciaDFollowerConfig(
        id="bimanual_follower",
        left_arm_port="/dev/ttyACM0",
        right_arm_port="/dev/ttyACM1",
        cameras={},  # 不需要相机
    )

    robot = make_robot_from_config(config)
    robot.connect()

    print("=" * 60)
    print("bi_alicia_d 状态监控 - 按 Ctrl+C 退出")
    print("将机械臂移动到期望的空闲位置，然后复制下方的状态值")
    print("=" * 60)

    try:
        while True:
            observation = robot.get_observation()

            # 格式化输出，方便复制
            print("\n" + "=" * 60)
            print("当前状态 (可直接复制作为 idle_action):")
            print("-" * 60)
            print("bi_alicia_d_idle_action = {")
            for key, value in observation.items():
                if key.endswith(".pos"):  # 只显示关节位置
                    print(f"    '{key}': {value:.8f},")
            print("}")
            print("-" * 60)
            print("按 Ctrl+C 停止")
            print("=" * 60)

            time.sleep(0.5)  # 0.5秒刷新一次

    except KeyboardInterrupt:
        print("\n程序已退出")
    finally:
        robot.disconnect()

if __name__ == "__main__":
    main()
