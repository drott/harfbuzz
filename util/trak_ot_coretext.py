#!/usr/bin/env python3
# Requires Pillow
# $ pip3 install Pillow
# Run as follows:
# $ cd ./util
# $ ./trak_ot_coretext.py (0|1|2) filename.png
# Open filename.png using "open" or "eog"
from PIL import Image, ImageOps, ImageDraw, ImageFont
from multiprocessing import Pool
import argparse
import io
import os
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("example_no", help="Choose example number", type=int)
parser.add_argument("filename", help="Output filename", type=str)
parser.add_argument(
    "--shape-data",
    help="Output hb-shape data to stdout for the same examples",
    action="store_true",
    default=False,
)
parser.add_argument("--align-ct-ot-start",
                    help="Try to align the start of the CoreText and OT AAT run",
                    action='store_true',
                    default=False)
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


def get_hb_shape_results_for_ptem_size(font_ptem_size):
    result = ""
    for shaper in shapers:
        hb_shape_command_line = [
            "./hb-shape",
            "--features=%s" % features,
            "--font-ptem=%d" % font_ptem_size,
            "--shaper=%s" % shaper,
            font_path,
            shape_text,
        ]
        result += "$ %s\n" % (" ".join(hb_shape_command_line))
        proc = subprocess.Popen(
            hb_shape_command_line, shell=False, stdout=subprocess.PIPE
        )
        result += proc.communicate()[0].decode("utf-8")
        result += "\n"
    return result


def write_hp_shape_data_to_file(p):
    hb_shape_data = retrieve_hp_shape_data(p)
    with open(args.filename, "a") as f:
        f.write(hb_shape_data)

def retrieve_hp_shape_data(p):
    hb_shape_data_for_ptem_sizes = p.map(
        get_hb_shape_results_for_ptem_size, font_ptem_sizes
    )
    hb_shape_data = ""
    for ptem_index, hb_shape_data_for_ptem in enumerate(
        hb_shape_data_for_ptem_sizes, 0
    ):
        hb_shape_data += "ptem: %s\n\n%s" % (font_ptem_sizes[ptem_index], hb_shape_data_for_ptem)
    return hb_shape_data


def extract_coretext_start_offset_corrections(p):
    hb_shape_results = retrieve_hp_shape_data(p)
    correction_offsets = []
    for match in re.finditer(r"\[\w+=0@([0-9\-]*),0\+", hb_shape_results, re.MULTILINE):
        correction_offsets.append(round(-int(match.groups()[0])/7))
    # print (correction_offsets)
    return correction_offsets

def perform_visual_comparison(p):
    if (args.align_ct_ot_start):
        correction_offsets = extract_coretext_start_offset_corrections(p)
    image_pairs = p.map(get_image_for_ptem_size, font_ptem_sizes)
    max_x = 0
    acc_y = 0
    for image in [image for image_pair in image_pairs for image in image_pair]:
        max_x = max(max_x, image.width)
        if (args.align_ct_ot_start):
            max_x += max(correction_offsets)
        acc_y += image.height
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
        ot_offset = (0,0)
        if (args.align_ct_ot_start):
            ot_offset = (correction_offsets[font_ptem_size_index], 0)
        alpha_blended.paste(
            ImageOps.colorize(image_ot, "Red", "White"),
            ot_offset,
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


if __name__ == "__main__":
    p = Pool(os.cpu_count() - 1)
    if not args.shape_data:
        perform_visual_comparison(p)
    else:
        write_hp_shape_data_to_file(p)
