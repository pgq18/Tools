#! /bin/bash

lerobot-record \
    --robot.type=alicia_d_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.cameras="{up: {type: intelrealsense, serial_number_or_name: 243322073287, width: 640, height: 480, fps: 15}, wrist: {type: intelrealsense, serial_number_or_name: 409122272488, width: 848, height: 480, fps: 30}}" \
    --robot.id=black \
    --teleop.type=alicia_d_leader \
    --teleop.id=leader_arm \
    --dataset.repo_id=ubuntu/grab-cube-dataset \
    --dataset.root=/home/mc509/Workspace/VLA/Aloha/datasets/test1 \
    --dataset.num_episodes=10 \
    --dataset.single_task="Grab the cube" \
    --dataset.episode_time_s=60 \
    --dataset.reset_time_s=30 \
    --display_data=true \
    --dataset.push_to_hub=false \
    # --resume=true