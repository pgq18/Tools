#!/bin/bash

python src/main.py \
    --robot.type=bi_alicia_d_follower \
    --robot.left_arm_port=/dev/ttyACM0 \
    --robot.right_arm_port=/dev/ttyACM1 \
    --robot.cameras="{up: {type: intelrealsense, serial_number_or_name: 243322073287, width: 640, height: 480, fps: 30}, wrist1: {type: intelrealsense, serial_number_or_name: 409122272488, width: 848, height: 480, fps: 30}, wrist2: {type: intelrealsense, serial_number_or_name: 409122273459, width: 848, height: 480, fps: 30}}" \
    --robot.id=bimanual_follower \
    --display_data=true \
    --server_host="192.168.60.202" \
    --task_description="Grab the stuff into the bowl" \
    --record_video true \
    --robot_type=bi_alicia_d
