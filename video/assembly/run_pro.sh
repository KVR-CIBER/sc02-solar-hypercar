#!/bin/bash
# The 'pro' render day on lvdell (RTX 3070): beauty stills -> steering film -> assembly film -> 360 turntable
cd "$(dirname "$0")"
B=/opt/blender-4.5.3-linux-x64/blender
enc() { ffmpeg -loglevel error -y -framerate 30 -i $1/%04d.png -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart $2_4k.mp4
        ffmpeg -loglevel error -y -i $2_4k.mp4 -vf scale=1920:-2 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart $2_1080p.mp4; }
echo "start $(date)" > progress.txt
$B -b -P scene_pro.py -- beauty > log_beauty.txt 2>&1; echo "beauty klaar $(date)" >> progress.txt
rm -rf steer; $B -b -P scene_pro.py -- steer > log_steer.txt 2>&1
python3 - <<'PY'
import json; json.dump(dict(fps=30, n=300, steps=[[1, 290, "Servo MG90S · stuurt ±20° via stuurhoorn en stuurstangen"]]), open('captions_steer.json', 'w'))
PY
python3 overlay.py captions_steer.json steer steer_final > log_ov_steer.txt 2>&1 || cp -r steer steer_final
enc steer_final sc02_sturen; echo "sturen klaar $(date)" >> progress.txt
rm -rf frames_pro; $B -b -P scene_pro.py -- anim > log_anim.txt 2>&1
python3 overlay.py captions_pro.json frames_pro final_pro > log_ov_anim.txt 2>&1
enc final_pro sc02_assemblage_pro; echo "assemblage klaar $(date)" >> progress.txt
rm -rf turn; $B -b -P scene_pro.py -- turntable > log_turn.txt 2>&1
enc turn sc02_360; echo "360 klaar $(date)" >> progress.txt
echo DONE > done_pro.txt
