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
_openpi_client_path = os.path.join(os.path.dirname(__file__), 'openpi_client')
if os.path.exists(_openpi_client_path):
    sys.path.insert(0, _openpi_client_path)
else:
    # Fallback to openpi package
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'openpi', 'packages', 'openpi-client', 'src'))

from openpi_client import msgpack_numpy

# SO101 idle action (home position)
SO101_IDLE_ACTION = {
    "shoulder_pan.pos": 4.13739266,
    "shoulder_lift.pos": -9.21443737,
    "elbow_flex.pos": -1.42267095,
    "wrist_flex.pos": 78.72523686,
    "wrist_roll.pos": 2.53860246,
    "gripper.pos": 18.26452064,
}


logger = logging.getLogger(__name__)


@dataclass
class RobotServerConfig:
    """Configuration for SO101 robot server."""
    port: int = 8001
    host: str = "0.0.0.0"
    robot_type: str = "so101"
    mock: bool = False


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
            if self._config.mock:
                logger.info(f"[Mock] Received action: {action}")
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._robot.send_action, action)
            return {"success": True, "action_sent": action}
        except Exception as e:
            logger.error(f"Error sending action: {e}")
            return {"success": False, "error": str(e)}

    async def _reset(self) -> Dict[str, Any]:
        """Reset robot to idle position."""
        try:
            if self._config.mock:
                logger.info("[Mock] Reset to idle position")
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._robot.send_action, SO101_IDLE_ACTION)
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
        except ImportError as e:
            logger.error(f"Real robot mode requires lerobot and draccus: {e}")
            logger.error("Use --mock for testing without hardware")
            return

        # Use draccus for the robot config
        @draccus.wrap()
        def create_robot(robot_cfg: RobotConfig):
            return robot_cfg

        # This is a simplified approach — in practice the full draccus config
        # would come from CLI args. For mock mode this is skipped entirely.
        logger.info("Creating robot...")
        robot = make_robot_from_config(config.robot)
        logger.info("Connecting to robot...")
        robot.connect()
        logger.info("Robot connected.")

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
