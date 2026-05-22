#!/bin/bash
# SO101 Robot Control Server
# Run on the machine connected to SO101 robot
#
# Usage:
#   Real robot:  bash so101_server.sh
#   Mock mode:   MOCK_ROBOT=true bash so101_server.sh

MOCK_ROBOT=false

# Server configuration
export ROBOT_PORT=${ROBOT_PORT:-8001}
export ROBOT_HOST=${ROBOT_HOST:-0.0.0.0}

# Mock mode flag
MOCK_FLAG=""
if [ "${MOCK_ROBOT:-false}" = "true" ]; then
    MOCK_FLAG="--mock"
    echo "Running in MOCK mode (no real robot)"
fi

if [ -z "$MOCK_FLAG" ]; then
    # Real robot configuration
    export SERIAL_PORT=${SERIAL_PORT:-COM3}
    export CAMERA_UP_INDEX=${CAMERA_UP_INDEX:-045322072659}
    export CAMERA_WRIST_INDEX=${CAMERA_WRIST_INDEX:-1}
    export ROBOT_ID=${ROBOT_ID:-my_awesome_follower_arm}

    python src/so101_robot_server.py \
        --robot.type=so101_follower \
        --robot.port=$SERIAL_PORT \
        --robot.id=$ROBOT_ID \
        --robot.cameras="{wrist: {type: opencv, index_or_path: $CAMERA_WRIST_INDEX, width: 640, height: 480, fps: 30}, up: {type: intelrealsense, serial_number_or_name: $CAMERA_UP_INDEX, width: 640, height: 480, fps: 30}}" \
        --port $ROBOT_PORT \
        --host $ROBOT_HOST \
        --robot_type so101
else
    # Mock mode — no hardware, no lerobot dependency
    python src/so101_robot_server.py \
        --port $ROBOT_PORT \
        --host $ROBOT_HOST \
        --robot_type so101 \
        $MOCK_FLAG
fi
