import os, sys
sys.path.insert(0, "/home/mc509/Workspace/VLA/Aloha/Tools")
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
    bi_alicia_d_follower,
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
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data
from lerobot.utils.robot_utils import precise_sleep

from openpi_client import websocket_client_policy as _websocket_client_policy
import numpy as np
import collections
import threading

RUNNING = False

so101_idle_action = {
    'shoulder_pan.pos': 4.13739266,
    'shoulder_lift.pos': -9.21443737,
    'elbow_flex.pos': -1.42267095,
    'wrist_flex.pos': 78.72523686,
    'wrist_roll.pos': 2.53860246,
    'gripper.pos': 18.26452064
    }

# 双臂 idle_action (需要根据实际机械臂调整数值)
bi_alicia_d_idle_action = {
    'left_joint1.pos': 0.17578125,
    'left_joint2.pos': -0.87890625,
    'left_joint3.pos': -0.52734375,
    'left_joint4.pos': -0.26367188,
    'left_joint5.pos': -0.87890625,
    'left_joint6.pos': -0.17578125,
    'left_gripper.pos': 502.00000000,
    'right_joint1.pos': -0.35156250,
    'right_joint2.pos': -0.70312500,
    'right_joint3.pos': -0.26367188,
    'right_joint4.pos': -0.08789063,
    'right_joint5.pos': -0.61523437,
    'right_joint6.pos': 0.08789063,
    'right_gripper.pos': 502.00000000,
}

# 机器人配置映射
ROBOT_CONFIGS = {
    "so101": {
        "state_keys": ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos",
                       "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"],
        "camera_mapping": {"front_view": "up", "left_wrist_view": "wrist"},
        "idle_action": so101_idle_action,
        "state_dim": 6,
    },
    "bi_alicia_d": {
        "state_keys": ["left_joint1.pos", "left_joint2.pos", "left_joint3.pos",
                       "left_joint4.pos", "left_joint5.pos", "left_joint6.pos", "left_gripper.pos",
                       "right_joint1.pos", "right_joint2.pos", "right_joint3.pos",
                       "right_joint4.pos", "right_joint5.pos", "right_joint6.pos", "right_gripper.pos"],
        "camera_mapping": {"face_view": "up", "left_wrist_view": "wrist1", "right_wrist_view": "wrist2"},
        "idle_action": bi_alicia_d_idle_action,
        "state_dim": 14,
    }
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
    # Robot type: "so101" or "bi_alicia_d"
    robot_type: str = "so101"
    # Dataset names for model inference
    dataset_names: list[str] = None

    def __post_init__(self):
        if self.dataset_names is None:
            self.dataset_names = ["penggq/task_0"]

def control_loop(robot: Robot, client, fps: int, display_data: bool = False, task_description: str | None = None,
                 record_video: bool = False, video_output_dir: str = "./recorded_videos",
                 video_writer_ref = None, robot_type: str = "so101", dataset_names: list[str] = None):
    # 获取机器人配置
    robot_config = ROBOT_CONFIGS[robot_type]
    state_keys = robot_config["state_keys"]
    camera_mapping = robot_config["camera_mapping"]
    idle_action = robot_config["idle_action"]
    state_dim = robot_config["state_dim"]

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

        # 动态构建状态
        state = np.array([observation[key] for key in state_keys])

        # 动态构建 element
        element = {
            **{view_name: observation[obs_key] for view_name, obs_key in camera_mapping.items()},
            "state": state,
            "prompt": str(task_description),
            "dataset_names": dataset_names,
        }

        if display_data:
            ob_action = {key: observation[key] for key in state_keys}
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

            # 动态构建动作字典
            action_dict = {state_keys[i]: action[i] for i in range(state_dim)}

            # SO101 特殊处理: gripper 阈值
            if robot_type == "so101":
                action_dict["gripper.pos"] = 0.0 if action_dict["gripper.pos"] < 8.0 else action_dict["gripper.pos"]
                action_dict["gripper.pos"] = action_dict["gripper.pos"] + 3.0

            robot.send_action(action_dict)
            dt_s = time.perf_counter() - loop_start
            precise_sleep(1 / fps - dt_s)
            print("Action: ", action_dict)
        else:
            robot.send_action(idle_action)
            dt_s = time.perf_counter() - loop_start
            precise_sleep(1 / fps - dt_s)
            # print("等待启动中... 当前状态:", element["state"])
        # time.sleep(0.01)  # 避免过度占用CPU

@draccus.wrap()
def control_robot(cfg: ControlConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))
    if cfg.display_data:
        init_rerun(session_name="control_robot")
    client = _websocket_client_policy.WebsocketClientPolicy(cfg.server_host, cfg.server_port)
    robot = make_robot_from_config(cfg.robot)
    robot.connect()

    # 用于在控制循环中传递和释放视频写入器
    video_writer_ref = [None]  # 使用列表以便在闭包中修改

    try:
        control_loop(robot, client, cfg.fps, cfg.display_data, cfg.task_description,
                     cfg.record_video, cfg.video_output_dir, video_writer_ref, cfg.robot_type,
                     cfg.dataset_names)
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

