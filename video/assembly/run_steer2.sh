#!/bin/bash
cd "$(dirname "$0")"
rm -rf steer steer_final
/opt/blender-4.5.3-linux-x64/blender -b -P scene_pro.py -- steer > log_steer2.txt 2>&1
python3 overlay_steer.py > log_ov_steer2.txt 2>&1
ffmpeg -loglevel error -y -framerate 30 -i steer_final/%04d.png -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart sc02_sturen_4k.mp4
ffmpeg -loglevel error -y -i sc02_sturen_4k.mp4 -vf scale=1920:-2 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sc02_sturen_1080p.mp4
echo "sturen v2 klaar $(date)" >> progress.txt; echo DONE > done_steer2.txt
