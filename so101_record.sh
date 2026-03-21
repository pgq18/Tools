#!/bin/bash

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=my_awesome_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=my_awesome_leader_arm \
    --robot.cameras="{wrist: {type: opencv, index_or_path: 18, width: 640, height: 480, fps: 30}, up: {type: intelrealsense, serial_number_or_name: 045322072659, width: 640, height: 480, fps: 30}}" \
    --display_data=true \
    --dataset.repo_id=so101/pap_20260321 \
    --dataset.num_episodes=1 \
    --dataset.push_to_hub=false \
    --dataset.single_task="Grab the stuff into the bowl." \
    --dataset.root=/home/mc509/Workspace/VLA/Aloha/datasets/so101_pap_20260321 \
    --resume=true