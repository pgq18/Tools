#!/bin/bash

lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=my_awesome_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=my_awesome_leader_arm \
    --fps=60 \
    --robot.cameras="{wrist: {type: opencv, index_or_path: 18, width: 640, height: 480, fps: 30}, up: {type: intelrealsense, serial_number_or_name: 045322072659, width: 640, height: 480, fps: 30}}" \
    --display_data=true 
