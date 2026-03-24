lerobot-record \
    --robot.type=bi_alicia_d_follower \
    --robot.left_arm_port=/dev/ttyACM1 \
    --robot.right_arm_port=/dev/ttyACM0 \
    --robot.cameras="{
        up: {type: intelrealsense, serial_number_or_name: 243322073287, width: 640, height: 480, fps: 15}, 
        wrist1: {type: intelrealsense, serial_number_or_name: 409122272488, width: 848, height: 480, fps: 30},
        wrist2: {type: intelrealsense, serial_number_or_name: 409122273459, width: 848, height: 480, fps: 30}
    }" \
    --robot.id=bimanual_follower \
    --teleop.type=bi_alicia_d_leader \
    --teleop.id=bimanual_leader \
    --dataset.repo_id=ubuntu/bimanual-grab-cube-dataset \
    --dataset.root=/home/mc509/Workspace/VLA/Aloha/datasets/test2026-03-04 \
    --dataset.num_episodes=150 \
    --dataset.single_task="Grab the stuff into the bowl" \
    --dataset.episode_time_s=60 \
    --dataset.reset_time_s=30 \
    --display_data=true \
    --dataset.push_to_hub=false \
    --resume=true
    # --dataset.chunks_size=10 \
    # --dataset.data_files_size_in_mb=50 \
    # --dataset.video_files_size_in_mb=100 \
    # --resume=true