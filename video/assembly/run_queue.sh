#!/bin/bash
# One render at a time (three at once filled the 8 GB of the RTX 3070 and made every frame tile + crawl).
# Resumes: frames already on disk are skipped (use_overwrite off).
cd "$(dirname "$0")"
B=/opt/blender-4.5.3-linux-x64/blender
enc() { ffmpeg -loglevel error -y -framerate 30 -i $1/%04d.png -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart $2_4k.mp4
        ffmpeg -loglevel error -y -i $2_4k.mp4 -vf scale=1920:-2 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart $2_1080p.mp4; }
echo "wachtrij start $(date)" >> progress.txt
$B -b -P scene_pro.py -- steer > log_steer2.txt 2>&1
find steer -size 0 -delete; python3 overlay_steer.py > log_ov_steer2.txt 2>&1 && enc steer_final sc02_sturen && echo "sturen v2 klaar $(date)" >> progress.txt && echo DONE > done_steer2.txt
$B -b -P scene_pro.py -- explain > log_explain.txt 2>&1
find frames_explain -size 0 -delete; python3 overlay_explain.py > log_ov_explain.txt 2>&1 && enc final_explain sc02_uitleg && echo "uitleg klaar $(date)" >> progress.txt && echo DONE > done_explain.txt
$B -b -P scene_pro.py -- anim > log_anim.txt 2>&1
find frames_pro -size 0 -delete; python3 overlay.py captions_pro.json frames_pro final_pro > log_ov_anim.txt 2>&1 && enc final_pro sc02_assemblage_pro && echo "assemblage klaar $(date)" >> progress.txt
$B -b -P scene_pro.py -- turntable > log_turn.txt 2>&1
find turn -size 0 -delete; enc turn sc02_360 && echo "360 klaar $(date)" >> progress.txt
echo DONE > done_pro.txt
