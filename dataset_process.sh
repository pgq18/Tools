#!/bin/bash

# ===========================
# ===== delete episodes =====
# ===========================
# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap151_20260321 \
#     --delete-episodes 0,1 \
#     --output /home/pengguanqi/Datasets/so101_pap150_20260321_filtered

# ==========================
# ===== visualize data =====
# ==========================
# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap151_20260321 \
#     --visualize \
#     --episode 40 \
#     --save ./tmp/ep40.png \
#     --save-video

# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap151_20260321 \
#     --generate-comparison \
#     --episode 1 \
#     --frames 0,50,100 \
#     --offsets -0.2 \
#     --output ./comparison.png


# ===========================
# ===== offset episodes =====
# ===========================
# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/piper_pap_20260629 \
#     --measure-offset \
#     --episode 2 \
#     --tolerance 0.13 \
#     --video-backend pyav

python src/dataset_process.py \
    --dataset-path /home/pengguanqi/Datasets/piper_pap_20260629 \
    --apply-offset \
    --offset-config /tmp/offset_config_piper_pap_20260629.yaml \
    --output /home/pengguanqi/Datasets/piper_pap_20260629_offset \
    --tolerance 0.06

# =========================
# ===== trim episodes =====
# =========================
# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap_20260429_offset \
#     --trim --trim-start 2.0 --trim-end 1.0 \
#     --output /home/pengguanqi/Datasets/so101_pap_20260429_offset_trimmed \
#     --video-backend pyav

# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap_20260429_offset \
#     --trim --trim-start 3.7 \
#     --output /home/pengguanqi/Datasets/so101_pap_20260429_offset_trimmed \
#     --video-backend pyav

# ==========================
# ===== merge datasets =====
# ==========================
# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/piper_pap_20260606_offset \
#     --merge-with /home/pengguanqi/Datasets/piper_pap_20260629_offset \
#     --output /home/pengguanqi/Datasets/piper_pap_20260606_20260629_offset_merged
