#!/usr/bin/env python
"""
SO101 Robot Server - WebSocket server for remote SO101 robot control.

Provides a network API for:
    - get_observation: Get robot state and camera images
    - send_action: Send joint position commands
    - reset: Reset robot to idle position
    - connect/disconnect: Connection management

Usage:
    # Real robot:
    python so101_robot_server.py \
        --robot.type=so101_follower \
        --robot.port=/dev/ttyACM0 \
        --robot.cameras="{up: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 1, width: 640, height: 480, fps: 30}}" \
        --port 8001

    # Mock mode (no hardware needed):
    python so101_robot_server.py --mock --port 8001
"""

import asyncio
import collections
import logging
import socket
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

# Import msgpack_numpy for serialization
import sys
import os

# Add openpi_client to path
_openpi_client_path = os.path.join(os.path.dirname(__file__), '..')
if os.path.exists(_openpi_client_path):
    sys.path.insert(0, _openpi_client_path)
else:
    # Fallback to openpi package
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'openpi', 'packages', 'openpi-client', 'src'))

from openpi_client import msgpack_numpy

# Lazy imports for real robot mode
# These are imported only when needed to avoid dependency issues in mock mode

# SO101 idle action (home position)
# SO101_IDLE_ACTION = {
#     "shoulder_pan.pos": 4.13739266,
#     "shoulder_lift.pos": -9.21443737,
#     "elbow_flex.pos": -1.42267095,
#     "wrist_flex.pos": 78.72523686,
#     "wrist_roll.pos": 2.53860246,
#     "gripper.pos": 18.26452064,
# }
SO101_IDLE_ACTION = {
    "shoulder_pan.pos": 8.0,
    "shoulder_lift.pos": -99.0,
    "elbow_flex.pos": 95.0,
    "wrist_flex.pos": 69.0,
    "wrist_roll.pos": 2.0,
    "gripper.pos": 2.0,
}

STATE_KEYS = [
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos",
]


def interpolate_new_chunk(last_action, new_chunk, interp_steps):
    """Linearly interpolate between last action and new chunk at boundary."""
    if interp_steps <= 0:
        return new_chunk
    chunk = new_chunk.copy()
    steps = min(interp_steps, len(chunk))
    for i in range(steps):
        alpha = (i + 1) / interp_steps
        chunk[i] = (1 - alpha) * last_action + alpha * new_chunk[i]
    return chunk


def mean_filter_deque(action_deque, window_size):
    """Apply sliding-window mean filter to the action deque in-place."""
    if window_size <= 1:
        return
    if window_size % 2 == 0:
        window_size += 1
    half_w = window_size // 2
    n = len(action_deque)
    items = list(action_deque)
    filtered = []
    for i in range(n):
        start = max(0, i - half_w)
        end = min(n, i + half_w + 1)
        filtered.append(np.mean(items[start:end], axis=0))
    action_deque.clear()
    action_deque.extend(filtered)


logger = logging.getLogger(__name__)


@dataclass
class RobotServerConfig:
    """Configuration for SO101 robot server."""
    port: int = 8001
    host: str = "0.0.0.0"
    robot_type: str = "so101"
    mock: bool = False
    reset_interp_steps: int = 20
    reset_step_delay: float = 0.05


class SO101RobotServer:
    """
    WebSocket server for SO101 robot control.

    Wraps SO101Follower and exposes network API.
    In mock mode, generates random observations without real hardware.
    """

    def __init__(self, robot, config: RobotServerConfig):
        self._robot = robot
        self._config = config
        self._packer = msgpack_numpy.Packer()
        self._connected_clients = set()
        self._last_action = None

    async def _handler(self, websocket):
        """Handle incoming WebSocket connection."""
        logger.info(f"New client connected from {websocket.remote_address}")
        self._connected_clients.add(websocket)

        try:
            # Send server metadata on connect
            metadata = {
                "robot_type": self._config.robot_type,
                "host": socket.gethostname(),
            }
            await websocket.send(self._packer.pack(metadata))

            # Handle requests
            async for message in websocket:
                try:
                    request = msgpack_numpy.unpackb(message)
                    response = await self._handle_request(request)
                    await websocket.send(self._packer.pack(response))
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    logger.error(traceback.format_exc())
                    # Send error as string (client will raise)
                    await websocket.send(f"Error: {e}\n{traceback.format_exc()}")

        except Exception as e:
            if "ConnectionClosed" in type(e).__name__:
                logger.info(f"Client disconnected: {websocket.remote_address}")
            else:
                logger.error(f"Handler error: {e}")
        finally:
            self._connected_clients.discard(websocket)

    async def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single request."""
        method = request.get("method")
        data = request.get("data", {})

        if method == "get_observation":
            return await self._get_observation()
        elif method == "send_action":
            return await self._send_action(data)
        elif method == "reset":
            return await self._reset()
        elif method == "get_metadata":
            return {"success": True, "metadata": {"robot_type": self._config.robot_type}}
        else:
            return {"success": False, "error": f"Unknown method: {method}"}

    async def _get_observation(self) -> Dict[str, Any]:
        """Get observation from robot (or generate mock data)."""
        try:
            if self._config.mock:
                obs = self._generate_mock_observation()
            else:
                loop = asyncio.get_event_loop()
                obs = await loop.run_in_executor(None, self._robot.get_observation)
            return {"success": True, "observation": obs}
        except Exception as e:
            logger.error(f"Error getting observation: {e}")
            return {"success": False, "error": str(e)}

    async def _send_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Send action to robot (or log in mock mode)."""
        try:
            self._last_action = action
            if self._config.robot_type == "so101":
                action["gripper.pos"] = 0.0 if action["gripper.pos"] < 8.0 else action["gripper.pos"]
                action["gripper.pos"] = action["gripper.pos"] + 3.0
            if self._config.mock:
                logger.info(f"[Mock] Received action: {action}")
            else:
                loop = asyncio.get_event_loop()
                print(action)
                await loop.run_in_executor(None, self._robot.send_action, action)
            return {"success": True, "action_sent": action}
        except Exception as e:
            logger.error(f"Error sending action: {e}")
            return {"success": False, "error": str(e)}

    async def _reset(self) -> Dict[str, Any]:
        """Reset robot to idle position with smooth interpolation."""
        try:
            if self._config.mock:
                logger.info("[Mock] Reset to idle position")
            else:
                loop = asyncio.get_event_loop()
                obs = await loop.run_in_executor(None, self._robot.get_observation)
                current = np.array([obs[key] for key in STATE_KEYS])
                target = np.array([SO101_IDLE_ACTION[key] for key in STATE_KEYS])

                # Build interpolation chunk: current → target
                chunk = np.linspace(current, target, self._config.reset_interp_steps)
                action_deque = collections.deque(chunk)
                mean_filter_deque(action_deque, 5)

                logger.info(f"Resetting to idle over {len(action_deque)} steps")
                for action_vec in action_deque:
                    action = {STATE_KEYS[j]: float(action_vec[j]) for j in range(len(STATE_KEYS))}
                    if self._config.robot_type == "so101":
                        action["gripper.pos"] = 0.0 if action["gripper.pos"] < 8.0 else action["gripper.pos"]
                        action["gripper.pos"] = action["gripper.pos"] + 3.0
                    await loop.run_in_executor(None, self._robot.send_action, action)
                    await asyncio.sleep(self._config.reset_step_delay)
                logger.info("Reset complete")

            return {"success": True}
        except Exception as e:
            logger.error(f"Error resetting: {e}")
            return {"success": False, "error": str(e)}

    def _generate_mock_observation(self) -> Dict[str, Any]:
        """Generate random observation for mock mode."""
        return {
            "shoulder_pan.pos": float(np.random.uniform(-10, 10)),
            "shoulder_lift.pos": float(np.random.uniform(-10, 10)),
            "elbow_flex.pos": float(np.random.uniform(-10, 10)),
            "wrist_flex.pos": float(np.random.uniform(0, 90)),
            "wrist_roll.pos": float(np.random.uniform(-5, 5)),
            "gripper.pos": float(np.random.uniform(0, 20)),
            "up": np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            "wrist": np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
        }

    async def serve(self):
        """Start WebSocket server."""
        import websockets.asyncio.server

        mode_str = "MOCK" if self._config.mock else "REAL"
        logger.info(f"Starting SO101 robot server ({mode_str}) on {self._config.host}:{self._config.port}")
        logger.info(f"Hostname: {socket.gethostname()}")

        async with websockets.asyncio.server.serve(
            self._handler,
            self._config.host,
            self._config.port,
            compression=None,
            max_size=None,
        ):
            logger.info("Server started. Press Ctrl+C to stop.")
            await asyncio.Future()  # Run forever


def main():
    """Main entry point with simple CLI argument parsing."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="SO101 Robot Server")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--mock", action="store_true", help="Mock mode (no real robot)")
    parser.add_argument("--robot_type", type=str, default="so101")
    args, remaining = parser.parse_known_args()

    config = RobotServerConfig(
        port=args.port,
        host=args.host,
        robot_type=args.robot_type,
        mock=args.mock,
    )

    logger.info(f"Configuration: {config}")

    robot = None
    if not config.mock:
        # Real robot mode — needs lerobot + draccus
        try:
            import draccus
            from lerobot.robots import RobotConfig, make_robot_from_config
            # Import robot configs to register them with draccus ChoiceRegistry
            from lerobot.robots.so101_follower import SO101FollowerConfig  # noqa: F401
            # Import camera configs to register them with draccus ChoiceRegistry
            from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
            from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig  # noqa: F401
        except ImportError as e:
            logger.error(f"Real robot mode requires lerobot and draccus: {e}")
            logger.error("Use --mock for testing without hardware")
            return

        # Create a wrapper config class that includes robot field
        # This allows --robot.type, --robot.port, etc. to work correctly
        @dataclass
        class RobotWrapperConfig:
            robot: RobotConfig = None

        # Parse robot config from remaining CLI args (--robot.type, --robot.port, etc.)
        logger.info("Creating robot...")
        wrapper_cfg = draccus.parse(RobotWrapperConfig, args=remaining)
        robot = make_robot_from_config(wrapper_cfg.robot)
        logger.info("Connecting to robot...")
        robot.connect()
        logger.info("Robot connected.")
        logger.info("Initializing robot to idle position...")
        robot.send_action(SO101_IDLE_ACTION)
        logger.info("Robot initialized to idle position.")

    server = SO101RobotServer(robot, config)

    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if robot is not None:
            logger.info("Disconnecting robot...")
            robot.disconnect()
            logger.info("Robot disconnected.")


if __name__ == "__main__":
    main()
