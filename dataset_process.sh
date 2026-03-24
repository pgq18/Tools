#!/bin/bash

# delete episodes
# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap151_20260321 \
#     --delete-episodes 0,1 \
#     --output /home/pengguanqi/Datasets/so101_pap150_20260321_filtered

# visualize data
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

python src/dataset_process.py \
    --dataset-path /home/pengguanqi/Datasets/so101_pap151_20260321_offset \
    --measure-offset \
    --episode 151 \
    --tolerance 0.04

# python src/dataset_process.py \
#     --dataset-path /home/pengguanqi/Datasets/so101_pap151_20260321 \
#     --apply-offset \
#     --offset-config calibration/dataset/offset_config_so101_pap151_20260321.yamloffset_config_so101_pap151_20260321.yaml \
#     --output /home/pengguanqi/Datasets/so101_pap151_20260321_offset \
#     --tolerance 0.04