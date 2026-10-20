#!/bin/bash
# Waits for the Luchtmeter render (one GPU), then renders the SC-02 assembly in 4K + overlays + H.264
cd "$(dirname "$0")"
while [ ! -f /opt/lm_video/done.txt ]; do sleep 60; done
set -e
rm -rf frames final; mkdir -p frames
/opt/blender-4.5.3-linux-x64/blender -b -P scene.py -- captions > log_captions.txt 2>&1
/opt/blender-4.5.3-linux-x64/blender -b -P scene.py -- anim > log_render.txt 2>&1
python3 overlay.py > log_overlay.txt 2>&1
ffmpeg -loglevel error -y -framerate 30 -i final/%04d.png -c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p -movflags +faststart sc02_assemblage_4k.mp4
ffmpeg -loglevel error -y -i sc02_assemblage_4k.mp4 -vf scale=1920:-2 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sc02_assemblage_1080p.mp4
echo DONE > done.txt
