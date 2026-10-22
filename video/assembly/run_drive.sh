#!/bin/bash
# driving film: render, overlay, encode, free the frames
cd /opt/sc02_video
rm -rf drive drive_final done_drive.txt
/opt/blender-4.5.3-linux-x64/blender -b -P scene_drive.py -- drive > log_drive.txt 2>&1
python3 overlay_drive.py > log_ov_drive.txt 2>&1
ffmpeg -loglevel error -y -framerate 30 -i drive_final/%04d.png -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -movflags +faststart sc02_rijden_4k.mp4
ffmpeg -loglevel error -y -i sc02_rijden_4k.mp4 -vf scale=1920:-2 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sc02_rijden_1080p.mp4
echo "rijden klaar $(date)" >> progress.txt; echo DONE > done_drive.txt; rm -rf drive drive_final
