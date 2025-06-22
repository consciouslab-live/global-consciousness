ffmpeg -f lavfi -i testsrc=duration=3600:size=1280x720:rate=30 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset veryfast -b:v 2500k -maxrate 2500k -bufsize 5000k \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -f flv "rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_STREAM_KEY"