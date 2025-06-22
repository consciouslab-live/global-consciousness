#!/usr/bin/env bash
source .env
RTMP="rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_STREAM_KEY"

ffmpeg -re -f image2pipe -vcodec png -r 30 -i /tmp/quantum_pipe \
  -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -pix_fmt yuv420p -preset veryfast \
  -b:v 2500k -maxrate 2500k -bufsize 5000k \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -f flv "$RTMP"