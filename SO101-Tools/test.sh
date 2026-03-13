#! /bin/bash

python main.py \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{wrist: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, up: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30}}" \
    --display_data=true \
    --server_host="192.168.60.202" \
    --task_description="Put green cube in the right bowl and red cube in the left bowl." \
    --record_video true
