#!/home/mc509/miniconda3/envs/aloha_lerobot/bin/python
"""
Human-in-the-Loop (HIL) Robot Control Script for SO101 Arms

This script implements online reinforcement learning with human intervention:
- Mode 1 (Autonomous): Follower controlled by model, leader tracks follower
- Mode 2 (Intervention): Leader controls follower, logs intervention data

Keyboard Controls:
  's' - Toggle between modes
  'q' - Exit program
"""

import logging
import time
import sys
import threading
import collections
from dataclasses import dataclass, field, asdict
from pprint import pformat
from datetime import datetime

import draccus
import numpy as np

from openpi_client import websocket_client_policy as _websocket_client_policy
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
    koch_leader,
    make_teleoperator_from_config,
    so100_leader,
    so101_leader,
)
from lerobot.utils.utils import init_logging
from lerobot.utils.robot_utils import precise_sleep

# Global state
MODE = 1  # 1 = autonomous (model control), 2 = intervention (leader control)
RUNNING = True

# SO101 state keys
STATE_KEYS = [
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos",
]


def keyboard_listener():
    """Listen for keyboard input to control mode switching."""
    global MODE, RUNNING
    print("\n" + "=" * 50)
    print("HIL Control - Keyboard Commands:")
    print("  's' - Toggle mode (Mode 1: Auto, Mode 2: Human)")
    print("  'q' - Exit program")
    print("=" * 50 + "\n")

    while True:
        try:
            char = input()
            if char.lower() == "s":
                MODE = 2 if MODE == 1 else 1
                mode_name = "Autonomous (Model)" if MODE == 1 else "Intervention (Human)"
                print(f"[MODE SWITCH] Now in Mode {MODE}: {mode_name}")
            elif char.lower() == "q":
                print("[EXIT] Shutting down...")
                RUNNING = False
                sys.exit(0)
        except EOFError:
            pass
        except Exception as e:
            print(f"[ERROR] Keyboard listener exception: {e}")


def enable_leader_torque(teleop: Teleoperator):
    """Enable torque on leader arm for active tracking."""
    if hasattr(teleop, 'bus'):
        for motor in teleop.bus.motors:
            teleop.bus.write("Torque_Enable", motor, 1)
        print("[INIT] Leader arm torque enabled for active tracking")
    else:
        print("[INIT] Leader arm does not support torque control")


def disable_leader_torque(teleop: Teleoperator):
    """Disable torque on leader arm for passive mode."""
    if hasattr(teleop, 'bus'):
        for motor in teleop.bus.motors:
            teleop.bus.write("Torque_Enable", motor, 0)
        print("[INIT] Leader arm torque disabled")
    else:
        print("[INIT] Leader arm does not support torque control")


def leader_track_follower(teleop: Teleoperator, follower_obs: dict):
    """Make leader arm follow follower arm position."""
    if hasattr(teleop, 'bus'):
        for motor in teleop.bus.motors:
            pos_key = f"{motor}.pos"
            if pos_key in follower_obs:
                teleop.bus.write("Goal_Position", motor, follower_obs[pos_key])


def build_element(observation: dict, task_description: str | None, dataset_name: str) -> dict:
    """Build element dict for model inference."""
    state = np.array([observation[key] for key in STATE_KEYS])
    return {
        "front_view": observation.get("up"),
        "left_wrist_view": observation.get("wrist"),
        "state": state,
        "prompt": str(task_description) if task_description else "",
        "dataset_names": [dataset_name],
    }


def build_action_dict(action: np.ndarray, state_keys: list) -> dict:
    """Convert action array to dict with SO101 gripper processing."""
    action_dict = {state_keys[i]: action[i] for i in range(len(state_keys))}
    # SO101 gripper threshold (from main.py)
    action_dict["gripper.pos"] = 0.0 if action_dict["gripper.pos"] < 8.0 else action_dict["gripper.pos"]
    action_dict["gripper.pos"] = action_dict["gripper.pos"] + 3.0
    return action_dict


def get_debug_action(debug_action_type: str, loop_count: int, fps: int) -> dict:
    """Generate debug action for Mode 1 in debug mode.

    Args:
        debug_action_type: "idle" for static, "cyclic" for sinusoidal motion
        loop_count: Current loop iteration count
        fps: Control loop frequency

    Returns:
        Action dict for SO101 follower
    """
    if debug_action_type == "idle":
        # Return static idle position
        return SO101_IDLE_ACTION.copy()

    elif debug_action_type == "cyclic":
        # Sinusoidal motion around idle position
        t = loop_count / fps  # time in seconds
        phase = 2 * np.pi * t / CYCLIC_PERIOD_S

        action = SO101_IDLE_ACTION.copy()
        # Apply sinusoidal offset to shoulder_pan and elbow_flex
        action["shoulder_pan.pos"] += CYCLIC_AMPLITUDE * np.sin(phase)
        action["elbow_flex.pos"] += CYCLIC_AMPLITUDE * np.sin(phase * 0.5)
        action["wrist_flex.pos"] += CYCLIC_AMPLITUDE * 0.5 * np.cos(phase)
        return action

    else:
        return SO101_IDLE_ACTION.copy()


@dataclass
class HILConfig:
    """Configuration for HIL robot control."""

    # Robot configs (using lerobot's RobotConfig for proper camera parsing)
    robot: RobotConfig
    teleop: TeleoperatorConfig

    # Model server
    server_host: str = "192.168.60.202"
    server_port: int = 8000

    # Control parameters
    fps: int = 60
    display_data: bool = False
    task_description: str | None = None
    dataset_name: str = "penggq/task_0"

    # Intervention logging
    log_interventions: bool = True
    intervention_log_dir: str = "./intervention_logs"

    # Debug mode
    debug_mode: bool = False
    # Debug action type: "idle" (静止) or "cyclic" (循环运动)
    debug_action_type: str = "idle"  # "idle" or "cyclic"


# SO101 idle action (from main.py)
SO101_IDLE_ACTION = {
    "shoulder_pan.pos": 4.13739266,
    "shoulder_lift.pos": -9.21443737,
    "elbow_flex.pos": -1.42267095,
    "wrist_flex.pos": 78.72523686,
    "wrist_roll.pos": 2.53860246,
    "gripper.pos": 18.26452064,
}

# Debug cyclic motion parameters
CYCLIC_AMPLITUDE = 5.0  # degrees
CYCLIC_PERIOD_S = 4.0  # seconds for one cycle


def hil_control_loop(
    teleop: Teleoperator,
    robot: Robot,
    client,
    fps: int,
    task_description: str | None,
    dataset_name: str,
    log_interventions: bool,
    intervention_log_dir: str,
    display_data: bool = False,
    debug_mode: bool = False,
    debug_action_type: str = "idle",
):
    """Main HIL control loop handling both autonomous and intervention modes."""
    global MODE, RUNNING

    # Start keyboard listener thread
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()

    # Action plan queue for model inference
    action_plan = collections.deque()

    # Intervention logging buffer
    intervention_buffer = []
    prev_mode = MODE

    # Loop counter for debug cyclic motion
    loop_count = 0

    # Enable leader torque for active tracking (Mode 1 starts by default)
    if MODE == 1:
        enable_leader_torque(teleop)

    print(f"[START] Beginning HIL control loop at {fps} FPS")
    print(f"[START] Initial mode: Mode {MODE} ({'Autonomous' if MODE == 1 else 'Intervention'})")
    if debug_mode:
        print(f"[DEBUG] Debug mode enabled, action type: {debug_action_type}")

    try:
        while RUNNING:
            loop_start = time.perf_counter()
            loop_count += 1

            # Detect mode switch -> clear action queue AND control leader torque
            if MODE != prev_mode:
                action_plan.clear()
                print(f"[MODE SWITCH] Cleared action queue (Mode {prev_mode} -> Mode {MODE})")

                # Control leader torque based on mode
                if MODE == 1:
                    # Entering Mode 1: Enable torque for active tracking
                    enable_leader_torque(teleop)
                    print("[MODE SWITCH] Leader torque ENABLED for active tracking")
                else:  # MODE == 2
                    # Entering Mode 2: Disable torque for human intervention
                    disable_leader_torque(teleop)
                    print("[MODE SWITCH] Leader torque DISABLED for human control")

                prev_mode = MODE

            # Get observations from both arms
            follower_obs = robot.get_observation()
            leader_action = teleop.get_action()

            if MODE == 1:
                # MODE 1: AUTONOMOUS - Model controls follower, leader tracks follower
                if debug_mode:
                    # Debug mode: use local debug action instead of model inference
                    action_dict = get_debug_action(debug_action_type, loop_count, fps)
                    robot.send_action(action_dict)
                    leader_track_follower(teleop, follower_obs)
                else:
                    # Normal mode: use model inference
                    if not action_plan:
                        try:
                            element = build_element(follower_obs, task_description, dataset_name)
                            action_chunk = client.infer(element)["action"][0]
                            action_plan.extend(action_chunk)
                            print(f"[INFERENCE] Received action chunk of length {len(action_chunk)}")
                        except Exception as e:
                            print(f"[ERROR] Model inference failed: {e}")
                            # Continue to next iteration if inference fails
                            dt_s = time.perf_counter() - loop_start
                            precise_sleep(1 / fps - dt_s)
                            continue

                    if action_plan:
                        action = action_plan.popleft()
                        action_dict = build_action_dict(action, STATE_KEYS)

                        # Send to follower
                        robot.send_action(action_dict)

                        # Leader actively tracks follower position
                        leader_track_follower(teleop, follower_obs)

            else:  # MODE == 2
                # MODE 2: INTERVENTION - Leader controls follower
                robot.send_action(leader_action)

                # Log intervention data
                if log_interventions:
                    state = np.array([follower_obs[key] for key in STATE_KEYS])
                    action = np.array([leader_action[key] for key in STATE_KEYS])
                    intervention_buffer.append({
                        "state": state,
                        "action": action,
                        "timestamp": time.time(),
                    })

            # Timing control
            dt_s = time.perf_counter() - loop_start
            precise_sleep(1 / fps - dt_s)

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Keyboard interrupt received")
    finally:
        # Save intervention buffer if not empty
        if log_interventions and intervention_buffer:
            save_intervention_buffer(intervention_buffer, intervention_log_dir)

        return intervention_buffer


def save_intervention_buffer(buffer: list, log_dir: str):
    """Save intervention data to disk."""
    import json
    import os

    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(log_dir, f"intervention_{timestamp}.json")

    # Convert numpy arrays to lists for JSON serialization
    serializable_buffer = []
    for entry in buffer:
        serializable_buffer.append({
            "state": entry["state"].tolist(),
            "action": entry["action"].tolist(),
            "timestamp": entry["timestamp"],
        })

    with open(filepath, "w") as f:
        json.dump(serializable_buffer, f, indent=2)

    print(f"[SAVE] Saved {len(buffer)} intervention records to {filepath}")


@draccus.wrap()
def run_hil(cfg: HILConfig):
    """Main entry point for HIL control."""
    init_logging()
    logging.info(pformat(asdict(cfg)))

    # Instantiate devices using lerobot's factory functions
    robot = make_robot_from_config(cfg.robot)
    teleop = make_teleoperator_from_config(cfg.teleop)

    # Create model client (skip in debug mode)
    if cfg.debug_mode:
        client = None
        print("\n" + "=" * 50)
        print("HIL Robot Control System [DEBUG MODE]")
        print("=" * 50)
    else:
        client = _websocket_client_policy.WebsocketClientPolicy(cfg.server_host, cfg.server_port)
        print("\n" + "=" * 50)
        print("HIL Robot Control System")
        print("=" * 50)

    print(f"Robot: {cfg.robot.id}")
    print(f"Teleop: {cfg.teleop.id}")
    if not cfg.debug_mode:
        print(f"Model Server: {cfg.server_host}:{cfg.server_port}")
    else:
        print(f"Debug Action Type: {cfg.debug_action_type}")
    print(f"FPS: {cfg.fps}")
    print("=" * 50 + "\n")

    # Connect devices
    print("[CONNECT] Connecting to teleoperator...")
    teleop.connect()
    print("[CONNECT] Connecting to robot...")
    robot.connect()
    print("[CONNECT] All devices connected!\n")

    try:
        intervention_buffer = hil_control_loop(
            teleop=teleop,
            robot=robot,
            client=client,
            fps=cfg.fps,
            task_description=cfg.task_description,
            dataset_name=cfg.dataset_name,
            log_interventions=cfg.log_interventions,
            intervention_log_dir=cfg.intervention_log_dir,
            display_data=cfg.display_data,
            debug_mode=cfg.debug_mode,
            debug_action_type=cfg.debug_action_type,
        )
        print(f"\n[DONE] Collected {len(intervention_buffer)} intervention samples")
    finally:
        # Disconnect devices
        print("\n[DISCONNECT] Disconnecting devices...")
        disable_leader_torque(teleop)
        teleop.disconnect()
        robot.disconnect()
        print("[DISCONNECT] All devices disconnected")


def main():
    run_hil()


if __name__ == "__main__":
    main()
