YOUTUBE_STREAM_KEY=$(grep '^YOUTUBE_STREAM_KEY=' .env | cut -d '=' -f2-)

RTMP="rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_STREAM_KEY"

# Open Ultra Low Latency for YouTube

ffmpeg -use_wallclock_as_timestamps 1 \
  -f lavfi -i "color=black:s=1280x720:r=30" \
  -f lavfi -i "anullsrc=cl=stereo:r=44100" \
  -vf "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:\
fontsize=90:fontcolor=#00ff99:\
textfile=/dev/shm/qbits.txt:reload=1:line_spacing=30:\
x=(w*2/3-tw)/2:y=(h-th)/2,\
drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:\
fontsize=60:fontcolor=#00ff99:\
text='%{localtime\\:%H\\\\\\:%M\\\\\\:%S}':\
x=(2*w/3)+(w/3-tw)/2:y=(h-th)/2" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset ultrafast -tune zerolatency -bf 0 -g 60 \
  -pix_fmt yuv420p \
  -b:v 2000k -maxrate 2000k -bufsize 4000k \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -threads 0 \
  -f flv "$RTMP"

# To export a single frame for debugging the layout, you can add: -frames:v 1 -y output.png