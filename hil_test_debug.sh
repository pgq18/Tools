#!/bin/bash
# Debug mode script - no remote server connection
# Robot arm will either stay idle or move in cyclic motion in Mode 1

python hil_test.py \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{wrist: {type: opencv, index_or_path: 18, width: 640, height: 480, fps: 30}, up: {type: intelrealsense, serial_number_or_name: 045322072659, width: 640, height: 480, fps: 15}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm \
    --fps=60 \
    --display_data=false \
    --log_interventions=true \
    --intervention_log_dir="./intervention_logs" \
    --debug_mode=true \
    --debug_action_type="cyclic"
    # debug_action_type options: "idle" (静止) or "cyclic" (循环运动)
