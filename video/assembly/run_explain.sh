#!/bin/bash
# SC-02 explainer film (runs next to run_pro.sh on the same GPU)
cd "$(dirname "$0")"
rm -rf frames_explain final_explain
/opt/blender-4.5.3-linux-x64/blender -b -P scene_pro.py -- explain > log_explain.txt 2>&1
python3 overlay_explain.py > log_ov_explain.txt 2>&1
ffmpeg -loglevel error -y -framerate 30 -i final_explain/%04d.png -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart sc02_uitleg_4k.mp4
ffmpeg -loglevel error -y -i sc02_uitleg_4k.mp4 -vf scale=1920:-2 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sc02_uitleg_1080p.mp4
echo "uitleg klaar $(date)" >> progress.txt; echo DONE > done_explain.txt
