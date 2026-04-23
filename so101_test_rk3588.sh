#!/bin/bash

python src/main.py \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{wrist: {type: opencv, index_or_path: 41, width: 640, height: 480, fps: 30}, up: {type: opencv, index_or_path: 47, width: 640, height: 480, fps: 30}}" \
    --display_data=false \
    --server_host="0.0.0.0" \
    --task_description="Grab the stuff into the bowl." \
    --record_video=false \
    --robot_type=so101 \
    --server_port=7999 \
    --dataset_names '["lerobot/so101"]' \
    --use_rtc=false \
    --rtc_s=16 \
    --rtc_d=10 \
    --rtc_action_horizon=32
