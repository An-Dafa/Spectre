import os
import random
import string
import textwrap

import cv2
import numpy as np
from faker import Faker
from PIL import Image, ImageDraw

from datagen_common import (
    SCENARIOS,
    apply_document_scenario,
    apply_nonlinear_warp,
    apply_thermal_fade,
    fit_font,
    generate_scenario_dataset,
    load_font,
    save_yolo_sample,
    text_bbox,
)


fake = Faker("id_ID")
CLASS_TEKS_SENSITIF = 3
CLASS_RESI = 8
OUTPUT_DIR = "datasets/resi_synth"
TOTAL_IMAGES = 1000
RESI_SCENARIOS = SCENARIOS + ["thermal_fade", "rolled_warp", "folded"]


def tracking_number():
    return random.choice(["JNE", "JNT", "SPX", "SCP", "NINJA"]) + "".join(
        random.choices(string.digits, k=random.randint(10, 14))
    )


def draw_sensitive(draw, position, text, font, boxes, anchor=None, padding=3):
    draw.text(position, text, font=font, fill=(20, 20, 20), anchor=anchor)
    boxes.append(
        (
            CLASS_TEKS_SENSITIF,
            *text_bbox(draw, position, text, font, anchor=anchor, padding=padding),
        )
    )


def draw_barcode(draw, box, seed):
    x1, y1, x2, y2 = box
    generator = random.Random(seed)
    x = x1
    while x < x2:
        width = generator.choice([2, 3, 4, 6])
        if generator.random() > 0.32:
            draw.rectangle((x, y1, min(x + width, x2), y2), fill=(8, 8, 8))
        x += width + generator.choice([2, 3, 5])


def wrap_address(address, width):
    return textwrap.wrap(address.replace("\n", ", ").upper(), width=width)


def render_portrait(img_idx):
    width = random.choice([720, 780, 840, 900, 960])
    height = random.choice([1050, 1200, 1400, 1600, 1800])
    image = Image.new("RGB", (width, height), (247, 246, 239))
    draw = ImageDraw.Draw(image)
    margin = max(28, width // 24)
    font_title = fit_font(draw, "J&T EXPRESS", width - margin * 2, width // 18, bold=True)
    font_header = load_font(max(20, width // 34), bold=True)
    font_body = load_font(max(17, width // 42))
    font_small = load_font(max(14, width // 52))
    font_tracking = fit_font(draw, "JNE12345678901234", width - margin * 2, width // 24, bold=True, mono=True)

    courier = random.choice(["JNE EXPRESS", "J&T EXPRESS", "SiCepat", "NINJA Xpress", "SPX EXPRESS"])
    tracking = tracking_number()
    sender = (fake.name().upper(), fake.phone_number(), fake.address())
    receiver = (fake.name().upper(), fake.phone_number(), fake.address())
    boxes = [(CLASS_RESI, 12, 12, width - 12, height - 12)]

    draw.rectangle((12, 12, width - 12, height - 12), outline=(45, 45, 45), width=3)
    draw.text((width / 2, margin), courier, font=font_title, fill=(20, 20, 20), anchor="ma")
    draw.text((margin, height * 0.085), "NO. RESI / AWB", font=font_small, fill=(70, 70, 70))
    draw_sensitive(draw, (margin, height * 0.11), tracking, font_tracking, boxes)

    barcode = (margin, round(height * 0.16), width - margin, round(height * 0.25))
    draw_barcode(draw, barcode, str(img_idx))
    boxes.append((CLASS_TEKS_SENSITIF, *barcode))

    sections = [
        ("PENGIRIM", sender, 0.30),
        ("PENERIMA", receiver, 0.53),
    ]
    for heading, values, y_fraction in sections:
        y = round(height * y_fraction)
        draw.line((margin, y - 18, width - margin, y - 18), fill=(55, 55, 55), width=2)
        draw.text((margin, y), heading, font=font_header, fill=(20, 20, 20))
        y += round(font_header.size * 1.4)
        draw_sensitive(draw, (margin, y), values[0], font_body, boxes)
        y += round(font_body.size * 1.45)
        draw_sensitive(draw, (margin, y), values[1], font_body, boxes)
        y += round(font_body.size * 1.5)
        for line in wrap_address(values[2], max(30, width // 15))[:5]:
            draw_sensitive(draw, (margin, y), line, font_small, boxes, padding=2)
            y += round(font_small.size * 1.4)

    footer_y = round(height * 0.79)
    draw.line((margin, footer_y, width - margin, footer_y), fill=(55, 55, 55), width=2)
    info = [
        f"LAYANAN : {random.choice(['REGULER', 'NEXT DAY', 'ECONOMY', 'SAME DAY'])}",
        f"BERAT   : {random.choice(['0.5 KG', '1 KG', '2 KG', '3 KG', '5 KG'])}",
        f"BIAYA   : Rp {random.randint(10, 250) * 1000:,}".replace(",", "."),
    ]
    for index, line in enumerate(info):
        info_xy = (
            margin,
            footer_y + 30 + index * round(font_body.size * 1.5),
        )
        draw_sensitive(draw, info_xy, line, font_body, boxes)
    draw.text(
        (width / 2, height - margin * 1.5),
        "DATA SINTETIS - BUKAN RESI ASLI",
        font=font_small,
        fill=(115, 115, 115),
        anchor="mm",
    )
    return image, boxes


def render_landscape(img_idx):
    width = random.choice([1100, 1250, 1400, 1550])
    height = random.choice([620, 720, 820, 920])
    image = Image.new("RGB", (width, height), (247, 246, 239))
    draw = ImageDraw.Draw(image)
    margin = max(28, width // 35)
    courier = random.choice(["JNE EXPRESS", "J&T EXPRESS", "SiCepat", "NINJA Xpress", "SPX EXPRESS"])
    tracking = tracking_number()
    sender = (fake.name().upper(), fake.phone_number(), fake.address())
    receiver = (fake.name().upper(), fake.phone_number(), fake.address())
    title_font = fit_font(draw, courier, width * 0.35, 38, bold=True)
    header_font = load_font(23, bold=True)
    body_font = load_font(19)
    small_font = load_font(15)
    tracking_font = fit_font(draw, tracking, width * 0.5, 31, bold=True, mono=True)
    boxes = [(CLASS_RESI, 12, 12, width - 12, height - 12)]

    draw.rectangle((12, 12, width - 12, height - 12), outline=(45, 45, 45), width=3)
    draw.text((margin, 35), courier, font=title_font, fill=(20, 20, 20))
    draw.text((width * 0.42, 28), "NO. RESI / AWB", font=small_font, fill=(70, 70, 70))
    tracking_xy = (width * 0.42, 55)
    draw_sensitive(draw, tracking_xy, tracking, tracking_font, boxes)

    barcode = (round(width * 0.42), 110, width - margin, 205)
    draw_barcode(draw, barcode, str(img_idx))
    boxes.append((CLASS_TEKS_SENSITIF, *barcode))
    draw.line((width / 2, 235, width / 2, height - 45), fill=(80, 80, 80), width=2)

    for column, (heading, values) in enumerate((("PENGIRIM", sender), ("PENERIMA", receiver))):
        x = margin if column == 0 else width / 2 + margin
        y = 250
        draw.text((x, y), heading, font=header_font, fill=(20, 20, 20))
        y += 42
        draw_sensitive(draw, (x, y), values[0], body_font, boxes)
        y += 32
        draw_sensitive(draw, (x, y), values[1], body_font, boxes)
        y += 35
        for line in wrap_address(values[2], max(28, width // 34))[:5]:
            draw_sensitive(draw, (x, y), line, small_font, boxes, padding=2)
            y += 24

    shipment_text = (
        f"{random.choice(['REGULER', 'NEXT DAY', 'ECONOMY'])} | "
        f"{random.choice(['0.5 KG', '1 KG', '2 KG', '3 KG'])} | "
        f"Rp {random.randint(10, 250) * 1000:,}".replace(",", ".")
    )
    shipment_font = fit_font(
        draw, shipment_text, width - margin * 2, 18, bold=True, min_size=12
    )
    draw_sensitive(
        draw,
        (margin, height - 38),
        shipment_text,
        shipment_font,
        boxes,
        padding=2,
    )

    draw.text(
        (width - margin, 226),
        "DATA SINTETIS",
        font=small_font,
        fill=(115, 115, 115),
        anchor="rs",
    )
    return image, boxes


def generate_resi_mockup(
    output_path,
    label_path,
    img_idx,
    scenario=None,
    orientation=None,
):
    orientation = orientation or random.choice(["portrait", "portrait", "landscape"])
    if orientation == "landscape":
        image, boxes = render_landscape(img_idx)
    else:
        image, boxes = render_portrait(img_idx)

    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    if scenario != "thermal_fade" and random.random() < 0.22:
        cv_image = apply_thermal_fade(cv_image)
    if scenario != "rolled_warp" and random.random() < 0.16:
        cv_image, boxes = apply_nonlinear_warp(
            cv_image,
            boxes,
            strength=random.uniform(0.012, 0.03),
        )

    cv_image, labels, _ = apply_document_scenario(
        cv_image,
        boxes,
        scenario=scenario,
        paper=True,
    )
    save_yolo_sample(
        cv_image,
        labels,
        os.path.join(output_path, f"resi_synth_{img_idx}.jpg"),
        os.path.join(label_path, f"resi_synth_{img_idx}.txt"),
    )
    return cv_image, labels


def generate_dataset(output_dir=OUTPUT_DIR, total_images=TOTAL_IMAGES, val_split=0.15):
    return generate_scenario_dataset(
        generate_resi_mockup,
        output_dir,
        total_images,
        scenarios=RESI_SCENARIOS,
        val_split=val_split,
    )


if __name__ == "__main__":
    generate_dataset()
