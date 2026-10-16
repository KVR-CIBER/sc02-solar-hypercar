#!/bin/zsh
# Publish to lvdell (Docker nginx, port 5880):
#   http://192.168.68.88:5880/      SC-02 hypercar free-drive simulation (f1/web)
#   http://192.168.68.88:5880/v1/   first version (lane sprint sim)
#   http://192.168.68.88:5880/files/  downloads (print files, DXF, firmware, Pi software, docs, video)
set -e
HOST=root@192.168.68.88
KEY=~/.ssh/proxmox_deploy
DIR="$(cd "$(dirname "$0")/.." && pwd)"
SSH=(ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes)
RS=(rsync -az --delete -e "ssh -i $KEY -o IdentitiesOnly=yes")
"$DIR/.venv/bin/python" "$DIR/tools/build_files_v2.py"
"${SSH[@]}" $HOST 'mkdir -p /opt/solar-sim/www /opt/solar-sim/conf'
"${RS[@]}" --exclude tmp/ --exclude preview.html --exclude files/ --exclude v1/ --exclude lijst/ "$DIR/f1/web/" $HOST:/opt/solar-sim/www/
"${RS[@]}" "$DIR/web/" $HOST:/opt/solar-sim/www/v1/
"${RS[@]}" "$DIR/f1/files/" $HOST:/opt/solar-sim/www/files/
"${RS[@]}" "$DIR/f1/lijst/" $HOST:/opt/solar-sim/www/lijst/
rsync -az -e "ssh -i $KEY -o IdentitiesOnly=yes" "$DIR/deploy/nginx.conf" $HOST:/opt/solar-sim/conf/default.conf
"${SSH[@]}" $HOST 'docker inspect solar-sim >/dev/null 2>&1 || docker run -d --name solar-sim --restart unless-stopped -p 5880:80 \
  -v /opt/solar-sim/www:/usr/share/nginx/html:ro -v /opt/solar-sim/conf:/etc/nginx/conf.d:ro nginx:alpine; docker exec solar-sim nginx -s reload'
echo "online: http://192.168.68.88:5880"
