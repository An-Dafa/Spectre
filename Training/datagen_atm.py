import os
import random

import cv2
import numpy as np
from faker import Faker
from PIL import Image, ImageDraw

from datagen_common import (
    SCENARIOS,
    apply_document_scenario,
    fit_font,
    generate_scenario_dataset,
    load_font,
    save_yolo_sample,
    text_bbox,
)


fake = Faker("id_ID")
CLASS_TEKS_SENSITIF = 3
CLASS_KARTU_ATM = 7
OUTPUT_DIR = "datasets/atm_synth"
TOTAL_IMAGES = 1000
CARD_WIDTH, CARD_HEIGHT = 856, 540

BANK_DESIGNS = [
    {"name": "BCA", "background": (25, 90, 170), "accent": (245, 180, 30), "text": (250, 250, 250)},
    {"name": "MANDIRI", "background": (30, 55, 130), "accent": (245, 180, 20), "text": (250, 250, 250)},
    {"name": "BNI", "background": (25, 125, 105), "accent": (235, 115, 35), "text": (250, 250, 250)},
    {"name": "BRI", "background": (35, 85, 170), "accent": (240, 240, 245), "text": (250, 250, 250)},
    {"name": "CIMB NIAGA", "background": (155, 25, 35), "accent": (235, 235, 235), "text": (250, 250, 250)},
    {"name": "BANK SYARIAH", "background": (40, 115, 75), "accent": (215, 180, 70), "text": (250, 250, 250)},
    {"name": "BANK DIGITAL", "background": (35, 30, 50), "accent": (135, 80, 220), "text": (245, 245, 250)},
]


def luhn_valid(number):
    digits = [int(char) for char in number if char.isdigit()]
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return bool(digits) and checksum % 10 == 0


def generate_non_luhn_card_number():
    while True:
        raw = "".join(str(random.randint(0, 9)) for _ in range(16))
        if not luhn_valid(raw):
            return raw, " ".join(raw[index:index + 4] for index in range(0, 16, 4))


def draw_card_text(draw, position, text, font, fill, embossed=False, anchor=None):
    if embossed:
        draw.text(
            (position[0] + 2, position[1] + 2),
            text,
            font=font,
            fill=(20, 20, 20),
            anchor=anchor,
        )
        draw.text(
            (position[0] - 1, position[1] - 1),
            text,
            font=font,
            fill=(255, 255, 255),
            anchor=anchor,
        )
    draw.text(position, text, font=font, fill=fill, anchor=anchor)


def draw_logo(draw, design):
    logo_box = (42, 30, 260, 105)
    draw.rounded_rectangle(
        logo_box,
        radius=12,
        fill=design["accent"],
        outline=(245, 245, 245),
        width=2,
    )
    logo_font = fit_font(draw, design["name"], 190, 31, bold=True, min_size=18)
    draw.text(
        ((logo_box[0] + logo_box[2]) / 2, (logo_box[1] + logo_box[3]) / 2),
        design["name"],
        font=logo_font,
        fill=(25, 25, 35),
        anchor="mm",
    )


def draw_chip(draw):
    x1, y1, x2, y2 = 70, 155, 235, 275
    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=17,
        fill=(210, 176, 75),
        outline=(100, 78, 25),
        width=3,
    )
    for x in (112, 165, 212):
        draw.line((x, y1, x, y2), fill=(110, 87, 35), width=2)
    draw.line((x1, 214, x2, 214), fill=(110, 87, 35), width=2)


def add_wear(image, amount=None):
    amount = amount if amount is not None else random.randint(2, 12)
    draw = ImageDraw.Draw(image, "RGBA")
    for _ in range(amount):
        start = (
            random.randint(5, image.width - 5),
            random.randint(5, image.height - 5),
        )
        end = (
            int(np.clip(start[0] + random.randint(-180, 180), 0, image.width)),
            int(np.clip(start[1] + random.randint(-45, 45), 0, image.height)),
        )
        draw.line((start, end), fill=(235, 235, 235, random.randint(35, 100)), width=random.choice([1, 1, 2]))
    if random.random() < 0.55:
        for margin in range(random.randint(2, 8)):
            alpha = max(12, 55 - margin * 6)
            draw.rounded_rectangle(
                (margin, margin, image.width - margin - 1, image.height - margin - 1),
                radius=25,
                outline=(245, 245, 245, alpha),
                width=1,
            )


def render_front(design, card_number, holder_name, expiry, embossed):
    image = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), design["background"])
    draw = ImageDraw.Draw(image)
    draw_logo(draw, design)
    draw_chip(draw)

    if random.random() < 0.7:
        for _ in range(random.randint(3, 7)):
            y = random.randint(115, CARD_HEIGHT - 40)
            color = tuple(min(255, channel + random.randint(15, 60)) for channel in design["background"])
            draw.arc((-120, y - 160, CARD_WIDTH + 140, y + 160), 190, 345, fill=color, width=random.randint(2, 8))

    number_font = fit_font(draw, card_number, CARD_WIDTH - 95, 41, bold=True, mono=True, min_size=28)
    name_font = fit_font(draw, holder_name, 500, 27, bold=True, min_size=17)
    small_font = load_font(16)
    expiry_font = load_font(25, bold=True)
    text_color = design["text"]
    boxes = [(CLASS_KARTU_ATM, 5, 5, CARD_WIDTH - 5, CARD_HEIGHT - 5)]

    number_xy = (48, 320)
    draw_card_text(draw, number_xy, card_number, number_font, text_color, embossed)
    boxes.append(
        (CLASS_TEKS_SENSITIF, *text_bbox(draw, number_xy, card_number, number_font, padding=5))
    )

    draw.text((50, 392), "VALID THRU", font=small_font, fill=text_color)
    expiry_xy = (155, 385)
    draw_card_text(draw, expiry_xy, expiry, expiry_font, text_color, embossed)
    boxes.append(
        (CLASS_TEKS_SENSITIF, *text_bbox(draw, expiry_xy, expiry, expiry_font))
    )

    name_xy = (50, 452)
    draw_card_text(draw, name_xy, holder_name, name_font, text_color, embossed)
    boxes.append(
        (CLASS_TEKS_SENSITIF, *text_bbox(draw, name_xy, holder_name, name_font))
    )
    draw.text(
        (CARD_WIDTH - 35, CARD_HEIGHT - 25),
        random.choice(["DEBIT", "GPN", "VISA", "MASTERCARD"]),
        font=load_font(20, bold=True),
        fill=text_color,
        anchor="rs",
    )
    return image, boxes


def render_back(design, raw_card_number, account_number, cvv, layout):
    darker = tuple(max(0, channel - 20) for channel in design["background"])
    image = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), darker)
    draw = ImageDraw.Draw(image)
    boxes = [(CLASS_KARTU_ATM, 5, 5, CARD_WIDTH - 5, CARD_HEIGHT - 5)]

    draw.rectangle((0, 75, CARD_WIDTH, 190), fill=(25, 25, 30))
    draw.rectangle((55, 225, 650, 315), fill=(242, 240, 224))
    draw.rectangle((650, 240, 800, 300), fill=(255, 255, 255))
    small = load_font(17)
    body = load_font(22, bold=True)
    mono = load_font(25, bold=True, mono=True)
    draw.text((60, 200), "AUTHORIZED SIGNATURE", font=small, fill=(235, 235, 235))

    cvv_xy = (665, 255)
    draw.text(cvv_xy, cvv, font=body, fill=(20, 20, 20))
    boxes.append((CLASS_TEKS_SENSITIF, *text_bbox(draw, cvv_xy, cvv, body)))

    if layout == "combined_panel":
        account_text = f"REK {account_number}"
        account_font = fit_font(draw, account_text, 535, 21, bold=True, mono=True)
        account_xy = (75, 255)
        draw.text(account_xy, account_text, font=account_font, fill=(30, 30, 30))
        boxes.append(
            (
                CLASS_TEKS_SENSITIF,
                *text_bbox(draw, account_xy, account_text, account_font),
            )
        )
    elif layout == "account_separate":
        label = "NO. REKENING"
        account_xy = (55, 355)
        draw.text(account_xy, label, font=small, fill=(245, 245, 245))
        value_xy = (55, 380)
        draw.text(value_xy, account_number, font=mono, fill=(245, 245, 245))
        boxes.append(
            (CLASS_TEKS_SENSITIF, *text_bbox(draw, value_xy, account_number, mono))
        )

    if layout in ("card_number_back", "combined_panel"):
        formatted = " ".join(raw_card_number[index:index + 4] for index in range(0, 16, 4))
        number_xy = (55, 440 if layout == "combined_panel" else 370)
        number_font = fit_font(draw, formatted, CARD_WIDTH - 110, 28, bold=True, mono=True)
        draw.text(number_xy, formatted, font=number_font, fill=(245, 245, 245))
        boxes.append(
            (CLASS_TEKS_SENSITIF, *text_bbox(draw, number_xy, formatted, number_font))
        )

    draw_logo(draw, design)
    draw.text(
        (CARD_WIDTH - 35, CARD_HEIGHT - 30),
        "DATA SINTETIS",
        font=small,
        fill=(235, 235, 235),
        anchor="rs",
    )
    return image, boxes


def combine_sides(front, front_boxes, back, back_boxes):
    gap = 32
    if random.random() < 0.5:
        canvas = Image.new(
            "RGB",
            (CARD_WIDTH * 2 + gap, CARD_HEIGHT),
            (215, 215, 215),
        )
        canvas.paste(front, (0, 0))
        canvas.paste(back, (CARD_WIDTH + gap, 0))
        shifted = [
            (class_id, x1 + CARD_WIDTH + gap, y1, x2 + CARD_WIDTH + gap, y2)
            for class_id, x1, y1, x2, y2 in back_boxes
        ]
    else:
        canvas = Image.new(
            "RGB",
            (CARD_WIDTH, CARD_HEIGHT * 2 + gap),
            (215, 215, 215),
        )
        canvas.paste(front, (0, 0))
        canvas.paste(back, (0, CARD_HEIGHT + gap))
        shifted = [
            (class_id, x1, y1 + CARD_HEIGHT + gap, x2, y2 + CARD_HEIGHT + gap)
            for class_id, x1, y1, x2, y2 in back_boxes
        ]
    return canvas, front_boxes + shifted


def generate_atm_mockup(
    output_path,
    label_path,
    img_idx,
    scenario=None,
    side_mode=None,
):
    design = random.choice(BANK_DESIGNS)
    raw_number, formatted_number = generate_non_luhn_card_number()
    holder_name = fake.name().upper()[:28]
    expiry = f"{random.randint(1, 12):02d}/{random.randint(27, 32):02d}"
    account_number = "".join(str(random.randint(0, 9)) for _ in range(random.randint(10, 13)))
    cvv = f"{random.randint(0, 999):03d}"
    embossed = random.random() < 0.5
    layout = random.choice(
        ["cvv_only", "account_separate", "card_number_back", "combined_panel"]
    )
    side_mode = side_mode or random.choices(
        ["front", "back", "both"], weights=[4, 3, 3], k=1
    )[0]

    front, front_boxes = render_front(
        design, formatted_number, holder_name, expiry, embossed
    )
    back, back_boxes = render_back(
        design, raw_number, account_number, cvv, layout
    )
    if random.random() < 0.7:
        add_wear(front)
    if random.random() < 0.7:
        add_wear(back)

    if side_mode == "front":
        document, boxes = front, front_boxes
    elif side_mode == "back":
        document, boxes = back, back_boxes
    else:
        document, boxes = combine_sides(front, front_boxes, back, back_boxes)

    cv_image = cv2.cvtColor(np.array(document), cv2.COLOR_RGB2BGR)
    cv_image, labels, _ = apply_document_scenario(
        cv_image,
        boxes,
        scenario=scenario,
        paper=False,
    )
    save_yolo_sample(
        cv_image,
        labels,
        os.path.join(output_path, f"atm_synth_{img_idx}.jpg"),
        os.path.join(label_path, f"atm_synth_{img_idx}.txt"),
    )
    return cv_image, labels


def generate_dataset(output_dir=OUTPUT_DIR, total_images=TOTAL_IMAGES, val_split=0.15):
    return generate_scenario_dataset(
        generate_atm_mockup,
        output_dir,
        total_images,
        scenarios=SCENARIOS,
        val_split=val_split,
    )


if __name__ == "__main__":
    generate_dataset()
