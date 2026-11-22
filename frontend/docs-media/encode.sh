#!/bin/sh
# Turn the recorded tour into docs/media/demo.mp4 and a lighter demo.gif for the README (needs ffmpeg).
set -e
V=$(ls -t test-results/*tour*/video.webm 2>/dev/null | head -1)
[ -n "$V" ] || { echo "no recorded tour found"; exit 0; }
mkdir -p ../docs/media
ffmpeg -y -v error -i "$V" -c:v libx264 -pix_fmt yuv420p -crf 24 -preset slow -movflags +faststart -an ../docs/media/demo.mp4
ffmpeg -y -v error -i "$V" -vf "fps=6,scale=840:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" ../docs/media/demo.gif
echo "docs/media/demo.mp4 and demo.gif updated"
