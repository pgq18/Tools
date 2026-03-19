import logging
import time
import draccus
from dataclasses import asdict, dataclass
from pprint import pformat
import rerun as rr
import cv2
from datetime import datetime
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    bi_so100_follower,
    hope_jr,
    koch_follower,
    make_robot_from_config,
    so100_follower,
    so101_follower,
)
from lerobot.teleoperators import (  # noqa: F401
    Teleoperator,
    TeleoperatorConfig,
    bi_so100_leader,
    gamepad,
    homunculus,
    koch_leader,
    make_teleoperator_from_config,
    so100_leader,
    so101_leader,
)
from lerobot.utils.utils import init_logging, move_cursor_up
from lerobot.utils.visualization_utils import _init_rerun, log_rerun_data
from lerobot.utils.robot_utils import busy_wait

from openpi_client import websocket_client_policy as _websocket_client_policy
import numpy as np
import collections
import threading
import sys

RUNNING = False

so101_idle_action = {
    'shoulder_pan.pos': 4.13739266,
    'shoulder_lift.pos': -9.21443737,
    'elbow_flex.pos': -1.42267095,
    'wrist_flex.pos': 78.72523686,
    'wrist_roll.pos': 2.53860246,
    'gripper.pos': 18.26452064
    }

def keyboard_listener():
    """监听键盘输入，在单独的线程中运行"""
    global RUNNING
    print("键盘控制说明:")
    print("按下 's' 键开始/停止机器人")
    print("按下 'q' 键退出程序")
    
    while True:
        try:
            char = input()  # 等待用户输入
            if char.lower() == 's':
                RUNNING = not RUNNING
                print(f"RUNNING状态已切换: {RUNNING}")
            elif char.lower() == 'q':
                print("正在退出程序...")
                RUNNING = False
                # 退出程序
                sys.exit(0)
        except EOFError:
            # 在某些系统上可能发生的错误，忽略它
            pass
        except Exception as e:
            print(f"键盘监听出现异常: {e}")


@dataclass
class ControlConfig:
    # TODO: pepijn, steven: if more robots require multiple teleoperators (like lekiwi) its good to make this possibele in teleop.py and record.py with List[Teleoperator]
    # teleop: TeleoperatorConfig
    robot: RobotConfig
    # Limit the maximum frames per second.
    fps: int = 60
    teleop_time_s: float | None = None
    # Display all cameras on screen
    display_data: bool = False
    server_host: str = "192.168.60.202"
    server_port: int = 8000
    task_description: str | None = None
    # Record up camera video
    record_video: bool = False
    # Video output directory
    video_output_dir: str = "./recorded_videos"

def control_loop(robot: Robot, client, fps: int, display_data: bool = False, task_description: str | None = None,
                 record_video: bool = False, video_output_dir: str = "./recorded_videos",
                 video_writer_ref = None):
    # 启动键盘监听线程
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()

    # 初始化视频录制器
    video_writer = None
    if video_writer_ref is None:
        video_writer_ref = [None]
    if record_video:
        import os
        os.makedirs(video_output_dir, exist_ok=True)
        # 注意：视频编码器需要在获取第一帧后初始化，因为需要知道帧的尺寸
        print(f"准备录制视频，输出目录: {video_output_dir}")

    action_plan = collections.deque()
    video_initialized = False
    while True:
        loop_start = time.perf_counter()
        observation = robot.get_observation()
        ob_action = {list(observation.keys())[i]: list(observation.values())[i] for i in range(6)}
        element = {
            "front_view": observation["up"],
            "left_wrist_view": observation["wrist"],
            "state": np.array(list(observation.values())[0:6]),
            "prompt": str(task_description),
            "dataset_names": ["penggq/task_0"],
        }
        if display_data:
            log_rerun_data(observation, ob_action)

        # 视频录制逻辑
        if record_video:
            up_frame = observation["up"]
            # 初始化视频写入器
            if not video_initialized and video_writer is None:
                height, width = up_frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                import os
                video_path = os.path.join(video_output_dir, f"up_camera_{timestamp}.mp4")
                video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
                video_writer_ref[0] = video_writer
                video_initialized = True
                print(f"开始录制视频到: {video_path}")

            # 写入视频帧
            if video_writer is not None:
                # 如果是 RGB 格式，需要转换为 BGR
                if len(up_frame.shape) == 3 and up_frame.shape[2] == 3:
                    frame = cv2.cvtColor(up_frame, cv2.COLOR_RGB2BGR)
                else:
                    frame = up_frame
                video_writer.write(frame)

        if RUNNING:
            if not action_plan:
                action_chunk = client.infer(element)["action"][0]
                action_plan.extend(action_chunk)
            action = action_plan.popleft()
            print("Action chunk: ", action)
            action = {list(observation.keys())[i]: action[i] for i in range(6)}
            action["gripper.pos"] = 0.0 if action["gripper.pos"] < 8.0 else action["gripper.pos"]
            action["gripper.pos"] = action["gripper.pos"] + 3.0
            robot.send_action(action)
            dt_s = time.perf_counter() - loop_start
            busy_wait(1 / fps - dt_s)
            print("Action: ", action)
        else:
            robot.send_action(so101_idle_action)
            dt_s = time.perf_counter() - loop_start
            busy_wait(1 / fps - dt_s)
            # print("等待启动中... 当前状态:", element["state"])
        # time.sleep(0.01)  # 避免过度占用CPU

@draccus.wrap()
def control_robot(cfg: ControlConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))
    if cfg.display_data:
        _init_rerun(session_name="control_robot")
    client = _websocket_client_policy.WebsocketClientPolicy(cfg.server_host, cfg.server_port)
    robot = make_robot_from_config(cfg.robot)
    robot.connect()

    # 用于在控制循环中传递和释放视频写入器
    video_writer_ref = [None]  # 使用列表以便在闭包中修改

    try:
        control_loop(robot, client, cfg.fps, cfg.display_data, cfg.task_description,
                     cfg.record_video, cfg.video_output_dir, video_writer_ref)
    except KeyboardInterrupt:
        pass
    finally:
        # 释放视频录制资源
        if video_writer_ref[0] is not None:
            video_writer_ref[0].release()
            print("视频录制已保存")
        if cfg.display_data:
            rr.rerun_shutdown()
        robot.disconnect()

def main():
    control_robot()

if __name__ == "__main__":
    main()

