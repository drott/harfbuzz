#!/usr/bin/env python3
# Requires Pillow
# $ pip3 install Pillow
# Run as follows:
# $ cd ./util
# $ ./trak_ot_coretext.py
# Open coretext_green_ot_red.png using "open" or "eog"
import subprocess
from multiprocessing import Pool
import os
from PIL import Image, ImageOps, ImageDraw, ImageFont
import io
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("example_no", help="Choose example number", type=int)
parser.add_argument("filename", help="Output filename", type=str)
args = parser.parse_args()

font_ptem_sizes = [
    3,
    # Trak table threshold for SFNSText.ttf from here...
    6,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    20,
    22,
    28,
    32,
    36,
    50,
    64,
    80,
    100,
    138,
    # until the line before here.
    150,
]
shapers = ["ot", "coretext"]
shape_text, font_path = [
    ("ABC", "../test/shaping/data/in-house/fonts/TestTRAK.ttf"),
    ("YoVa", "/System/Library/Fonts/SFNSText.ttf"),
    ("HH", "TestTRAKOne.ttf"),
][args.example_no]
features = "+kern"


def get_image_for_ptem_size(font_ptem_size):
    images = []
    for shaper in shapers:
        proc = subprocess.Popen(
            [
                "./hb-view",
                "--features=%s" % features,
                "--font-ptem=%d" % font_ptem_size,
                "--font-size=256",
                "--shaper=%s" % shaper,
                font_path,
                shape_text,
            ],
            shell=False,
            stdout=subprocess.PIPE,
        )
        images.append(Image.open(io.BytesIO(proc.communicate()[0])))
    return images


p = Pool(os.cpu_count() - 1)
image_pairs = p.map(get_image_for_ptem_size, font_ptem_sizes)

max_x = 0
acc_y = 0
for image in [image for image_pair in image_pairs for image in image_pair]:
    max_x = max(max_x, image.getbbox()[2])
    acc_y += image.getbbox()[3]
composite_image = Image.new("RGBA", (max_x, acc_y))
insert_position = 0
for font_ptem_size_index, (image_ot, image_coretext) in enumerate(image_pairs, 0):
    merged_size = (
        max(image_ot.width, image_coretext.width),
        max(image_ot.height, image_coretext.height),
    )
    alpha_blended = Image.new("RGBA", merged_size)
    alpha_blended.paste(
        ImageOps.colorize(image_coretext, "Green", "White"),
        (0, 0),
        Image.new("L", image_coretext.size, 255),
    )
    alpha_blended.paste(
        ImageOps.colorize(image_ot, "Red", "White"),
        (0, 0),
        Image.new("L", image_ot.size, 127),
    )
    draw_context = ImageDraw.Draw(alpha_blended)
    font = ImageFont.load_default()
    draw_context.text(
        (10, 10), "ptem: %s" % font_ptem_sizes[font_ptem_size_index], fill="Black"
    )
    composite_image.paste(alpha_blended, (0, insert_position))
    insert_position += merged_size[1]
composite_image.save(args.filename)
