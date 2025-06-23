import subprocess
import random
import time
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import os

load_dotenv()

YOUTUBE_STREAM_KEY = os.getenv("YOUTUBE_STREAM_KEY")

W, H, FPS = 1280, 720, 30
# W, H, FPS = 1280, 720, 1
FONT = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 280
)


# pre-render the only two possible frames
def make(bit):
    im = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(im)
    txt = str(bit)
    bbox = d.textbbox((0, 0), txt, font=FONT)
    x = (W - (bbox[2] - bbox[0])) // 2
    y = (H - (bbox[3] - bbox[1])) // 2
    d.text((x, y), txt, font=FONT, fill="#00ff99")
    return im.tobytes()  # raw RGB24 bytes


RAW = [make(0), make(1)]

RTMP = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"

cmd = [
    "ffmpeg",
    "-f",
    "rawvideo",
    "-pixel_format",
    "rgb24",
    "-video_size",
    f"{W}x{H}",
    "-framerate",
    str(FPS),
    "-i",
    "-",  # ← stdin
    "-f",
    "lavfi",
    "-i",
    "anullsrc=channel_layout=stereo:sample_rate=44100",
    "-map",
    "0:v:0",
    "-map",
    "1:a:0",
    "-c:v",
    "libx264",
    "-preset",
    "veryfast",
    "-tune",
    "zerolatency",
    "-pix_fmt",
    "yuv420p",
    "-b:v",
    "2500k",
    "-maxrate",
    "2500k",
    "-bufsize",
    "5000k",
    "-c:a",
    "aac",
    "-b:a",
    "128k",
    "-f",
    "flv",
    RTMP,
]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

while True:
    if proc.stdin is not None:
        proc.stdin.write(RAW[random.getrandbits(1)])
    time.sleep(1 / FPS)
