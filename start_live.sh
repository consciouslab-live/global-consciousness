#!/usr/bin/env bash

# Before running this script, make sure to create the named pipe (FIFO) for video frames:
# Run the following command in your terminal:
#   mkfifo /tmp/quantum_pipe


YOUTUBE_STREAM_KEY=$(grep '^YOUTUBE_STREAM_KEY=' .env | cut -d '=' -f2-)

RTMP="rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_STREAM_KEY"

ffmpeg -re -f image2pipe -vcodec png -r 30 -i /tmp/quantum_pipe \
  -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -pix_fmt yuv420p -preset veryfast \
  -b:v 2500k -maxrate 2500k -bufsize 5000k \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -f flv "$RTMP"