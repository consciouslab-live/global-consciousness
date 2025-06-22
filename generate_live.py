from PIL import Image, ImageDraw, ImageFont
import random
import time

W, H = 1280, 720
FPS = 30
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 280
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

pipe = open("/tmp/quantum_pipe", "wb", buffering=0)


def draw_frame(bit):
    im = Image.new("RGB", (W, H), "black")
    draw = ImageDraw.Draw(im)
    txt = str(bit)
    bbox = draw.textbbox((0, 0), txt, font=font)
    x = (W - (bbox[2] - bbox[0])) // 2
    y = (H - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), txt, font=font, fill="#00ff99")
    return im


while True:
    bit = random.randint(0, 1)
    frame = draw_frame(bit)
    for _ in range(FPS):
        frame.save(pipe, format="PNG")
        time.sleep(1 / FPS)
