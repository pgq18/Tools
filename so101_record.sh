#!/bin/bash

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm \
    --robot.cameras="{wrist: {type: opencv, index_or_path: 18, width: 640, height: 480, fps: 30}, up: {type: intelrealsense, serial_number_or_name: 045322072659, width: 640, height: 480, fps: 30}}" \
    --display_data=true \
    --dataset.repo_id=penggq/my_dataset \
    --dataset.num_episodes=2 \
    --dataset.single_task="Pick up the transparent roll, cover the toy duck with it, then place the blue cube inside the roll."