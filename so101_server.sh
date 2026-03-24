#!/bin/bash
# SO101 Robot Control Server
# Run on the machine connected to SO101 robot

# Server configuration
export ROBOT_PORT=${ROBOT_PORT:-8001}
export ROBOT_HOST=${ROBOT_HOST:-0.0.0.0}

# Serial port configuration
export SERIAL_PORT=${SERIAL_PORT:-/dev/ttyACM0}

# Camera configuration (adjust indices as needed)
export CAMERA_UP_INDEX=${CAMERA_UP_INDEX:-0}
export CAMERA_WRIST_INDEX=${CAMERA_WRIST_INDEX:-1}

# Robot ID
export ROBOT_ID=${ROBOT_ID:-so101_follower_arm}

python src/so101_robot_server.py \
    --robot.type=so101_follower \
    --robot.port=$SERIAL_PORT \
    --robot.id=$ROBOT_ID \
    --robot.cameras="{up: {type: opencv, index_or_path: $CAMERA_UP_INDEX, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: $CAMERA_WRIST_INDEX, width: 640, height: 480, fps: 30}}" \
    --port $ROBOT_PORT \
    --host $ROBOT_HOST \
    --robot_type so101
