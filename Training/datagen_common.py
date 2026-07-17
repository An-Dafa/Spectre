import math
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


SCENARIOS = [
    "normal",
    "tilt_mild",
    "tilt_strong",
    "far_away",
    "close_up",
    "perspective",
    "finger_occlusion",
    "stacked_docs",
    "scattered_cards",
    "face_background",
    "dark_lighting",
    "bright_overexp",
    "glare_reflection",
    "shadow_partial",
    "motion_blur",
    "rotation_free",
    "damaged_card",
    "complex_bg",
    "paper_crumple",
    "scan_artifact",
]

CLASS_NAMES = {
    0: "ktp",
    1: "sim",
    2: "paspor",
    3: "teks_sensitif",
    4: "wajah",
    5: "plat_nomor",
    6: "kk",
    7: "kartu_atm",
    8: "resi",
}

MIN_VISIBLE = 0.5


def load_font(size, bold=False, mono=False):
    if mono:
        names = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"]
    elif bold:
        names = ["arialbd.ttf", "DejaVuSans-Bold.ttf"]
    else:
        names = ["arial.ttf", "DejaVuSans.ttf"]

    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def text_bbox(draw, xy, text, font, anchor=None, padding=3):
    if "\n" in text:
        x1, y1, x2, y2 = draw.multiline_textbbox(
            xy, text, font=font, anchor=anchor, spacing=4
        )
    else:
        x1, y1, x2, y2 = draw.textbbox(xy, text, font=font, anchor=anchor)
    return x1 - padding, y1 - padding, x2 + padding, y2 + padding


def fit_font(draw, text, max_width, start_size, bold=False, mono=False, min_size=8):
    for size in range(start_size, min_size - 1, -1):
        font = load_font(size, bold=bold, mono=mono)
        x1, _, x2, _ = draw.textbbox((0, 0), text, font=font)
        if x2 - x1 <= max_width:
            return font
    return load_font(min_size, bold=bold, mono=mono)


def generate_synthetic_portrait(width, height):
    """Potret prosedural offline. Return (PIL image, bbox wajah xyxy)."""
    background = random.choice(
        [(190, 35, 40), (35, 70, 175), (185, 185, 190), (220, 220, 215)]
    )
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    skin = random.choice(
        [
            (244, 205, 168),
            (226, 177, 132),
            (199, 143, 101),
            (158, 103, 72),
            (112, 72, 55),
        ]
    )
    shirt = tuple(random.randint(25, 180) for _ in range(3))
    hair = random.choice(
        [(20, 16, 14), (45, 29, 20), (72, 46, 28), (16, 16, 20)]
    )

    face_width = round(width * random.uniform(0.5, 0.62))
    face_height = round(height * random.uniform(0.52, 0.62))
    face_x1 = (width - face_width) // 2 + random.randint(-width // 25, width // 25)
    face_y1 = round(height * random.uniform(0.14, 0.2))
    face_x2, face_y2 = face_x1 + face_width, face_y1 + face_height

    draw.ellipse(
        (
            round(width * 0.08),
            round(height * 0.73),
            round(width * 0.92),
            round(height * 1.18),
        ),
        fill=shirt,
    )
    neck_width = round(face_width * 0.27)
    draw.rectangle(
        (
            (width - neck_width) // 2,
            round(face_y2 * 0.88),
            (width + neck_width) // 2,
            round(height * 0.82),
        ),
        fill=skin,
    )

    hijab = random.random() < 0.24
    if hijab:
        hijab_color = tuple(random.randint(25, 185) for _ in range(3))
        draw.ellipse(
            (
                face_x1 - round(face_width * 0.2),
                face_y1 - round(face_height * 0.13),
                face_x2 + round(face_width * 0.2),
                face_y2 + round(face_height * 0.3),
            ),
            fill=hijab_color,
        )
    else:
        draw.ellipse(
            (
                face_x1 - round(face_width * 0.06),
                face_y1 - round(face_height * 0.08),
                face_x2 + round(face_width * 0.06),
                face_y1 + round(face_height * 0.48),
            ),
            fill=hair,
        )

    ear_width = max(2, round(face_width * 0.1))
    ear_y1, ear_y2 = (
        face_y1 + round(face_height * 0.37),
        face_y1 + round(face_height * 0.61),
    )
    draw.ellipse((face_x1 - ear_width // 2, ear_y1, face_x1 + ear_width, ear_y2), fill=skin)
    draw.ellipse((face_x2 - ear_width, ear_y1, face_x2 + ear_width // 2, ear_y2), fill=skin)
    draw.ellipse((face_x1, face_y1, face_x2, face_y2), fill=skin)

    if not hijab:
        hairline = face_y1 + round(face_height * random.uniform(0.13, 0.22))
        draw.pieslice(
            (face_x1 - 2, face_y1 - round(face_height * 0.13), face_x2 + 2, hairline + round(face_height * 0.2)),
            180,
            360,
            fill=hair,
        )

    eye_y = face_y1 + round(face_height * 0.43)
    eye_offset = round(face_width * 0.2)
    eye_radius = max(1, round(face_width * 0.025))
    center_x = (face_x1 + face_x2) // 2
    for eye_x in (center_x - eye_offset, center_x + eye_offset):
        draw.line(
            (
                eye_x - eye_radius * 2,
                eye_y - eye_radius * 2,
                eye_x + eye_radius * 2,
                eye_y - eye_radius * 3,
            ),
            fill=hair,
            width=max(1, eye_radius),
        )
        draw.ellipse(
            (
                eye_x - eye_radius,
                eye_y - eye_radius,
                eye_x + eye_radius,
                eye_y + eye_radius,
            ),
            fill=(25, 22, 20),
        )

    nose_y = face_y1 + round(face_height * 0.61)
    draw.line(
        (
            center_x,
            eye_y + eye_radius * 2,
            center_x - eye_radius,
            nose_y,
            center_x + eye_radius * 2,
            nose_y,
        ),
        fill=tuple(max(0, value - 45) for value in skin),
        width=max(1, eye_radius),
    )
    mouth_y = face_y1 + round(face_height * 0.76)
    mouth_width = round(face_width * random.uniform(0.18, 0.27))
    draw.arc(
        (
            center_x - mouth_width,
            mouth_y - eye_radius * 2,
            center_x + mouth_width,
            mouth_y + eye_radius * 4,
        ),
        10,
        170,
        fill=random.choice([(105, 35, 35), (135, 55, 60), (80, 40, 35)]),
        width=max(1, eye_radius),
    )

    if random.random() < 0.22:
        glasses_color = random.choice([(20, 20, 20), (70, 55, 40), (35, 60, 95)])
        lens_width, lens_height = round(face_width * 0.25), round(face_height * 0.13)
        for eye_x in (center_x - eye_offset, center_x + eye_offset):
            draw.rounded_rectangle(
                (
                    eye_x - lens_width // 2,
                    eye_y - lens_height // 2,
                    eye_x + lens_width // 2,
                    eye_y + lens_height // 2,
                ),
                radius=max(1, lens_height // 5),
                outline=glasses_color,
                width=max(1, eye_radius),
            )
        draw.line(
            (center_x - eye_offset + lens_width // 2, eye_y, center_x + eye_offset - lens_width // 2, eye_y),
            fill=glasses_color,
            width=max(1, eye_radius),
        )

    if not hijab and random.random() < 0.18:
        draw.arc(
            (
                center_x - round(face_width * 0.18),
                mouth_y - round(face_height * 0.09),
                center_x + round(face_width * 0.18),
                mouth_y + round(face_height * 0.02),
            ),
            0,
            180,
            fill=hair,
            width=max(1, round(face_height * 0.025)),
        )

    array = np.array(image)
    array = add_gaussian_noise(array, random.uniform(1.5, 5))
    if random.random() < 0.45:
        array = cv2.GaussianBlur(array, (3, 3), 0)
    return Image.fromarray(array), (face_x1, face_y1, face_x2, face_y2)


def add_gaussian_noise(image, sigma):
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def bbox_area(box):
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def clip_bbox(box, width, height):
    x1, y1, x2, y2 = box
    return (
        float(np.clip(x1, 0, width)),
        float(np.clip(y1, 0, height)),
        float(np.clip(x2, 0, width)),
        float(np.clip(y2, 0, height)),
    )


def compute_visible_ratio(target_rect, occluder_rects):
    """Rasio bbox yang masih terlihat. Sengaja berada di level modul."""
    x1, y1, x2, y2 = target_rect
    if bbox_area(target_rect) <= 0:
        return 0.0
    if not occluder_rects:
        return 1.0

    xs = np.linspace(x1, x2, 20)
    ys = np.linspace(y1, y2, 20)
    visible = 0
    for y in ys:
        for x in xs:
            covered = any(
                ox1 <= x <= ox2 and oy1 <= y <= oy2
                for ox1, oy1, ox2, oy2 in occluder_rects
            )
            visible += not covered
    return visible / (len(xs) * len(ys))


def project_bbox_affine(box, matrix):
    x1, y1, x2, y2 = box
    points = np.float32(
        [[x1, y1, 1], [x2, y1, 1], [x2, y2, 1], [x1, y2, 1]]
    )
    transformed = (matrix @ points.T).T
    return (
        float(transformed[:, 0].min()),
        float(transformed[:, 1].min()),
        float(transformed[:, 0].max()),
        float(transformed[:, 1].max()),
    )


def project_bbox_perspective(box, matrix):
    x1, y1, x2, y2 = box
    points = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
    transformed = cv2.perspectiveTransform(points.reshape(-1, 1, 2), matrix)
    transformed = transformed.reshape(-1, 2)
    return (
        float(transformed[:, 0].min()),
        float(transformed[:, 1].min()),
        float(transformed[:, 0].max()),
        float(transformed[:, 1].max()),
    )


def boxes_to_yolo(boxes, width, height, document_class=None):
    labels = []
    for class_id, x1, y1, x2, y2 in boxes:
        original_area = bbox_area((x1, y1, x2, y2))
        x1, y1, x2, y2 = clip_bbox((x1, y1, x2, y2), width, height)
        if x2 - x1 < 3 or y2 - y1 < 3:
            continue
        visible = bbox_area((x1, y1, x2, y2)) / max(1.0, original_area)
        if class_id != document_class and visible < MIN_VISIBLE:
            continue
        labels.append(
            (
                class_id,
                (x1 + x2) / 2 / width,
                (y1 + y2) / 2 / height,
                (x2 - x1) / width,
                (y2 - y1) / height,
            )
        )
    return labels


def rotate_image_and_boxes(image, boxes, angle, border_value):
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderValue=border_value,
    )
    transformed = [
        (class_id, *project_bbox_affine((x1, y1, x2, y2), matrix))
        for class_id, x1, y1, x2, y2 in boxes
    ]
    return rotated, boxes_to_yolo(transformed, width, height, boxes[0][0])


def paper_border_value():
    return (
        random.randint(240, 255),
        random.randint(240, 255),
        random.randint(235, 250),
    )


def make_background(kind, width, height):
    if kind == "desk_wood":
        base = np.full((height, width, 3), (55, 90, 135), dtype=np.float32)
        stripes = np.sin(np.arange(height)[:, None] * 0.055) * 12
        base += stripes[:, :, None]
    elif kind == "cloth_dark":
        base = np.full((height, width, 3), (38, 35, 42), dtype=np.float32)
    elif kind == "cloth_light":
        base = np.full((height, width, 3), (205, 200, 195), dtype=np.float32)
    elif kind == "concrete":
        base = np.full((height, width, 3), (150, 148, 145), dtype=np.float32)
    elif kind == "hand_skin":
        base = np.full((height, width, 3), (125, 165, 210), dtype=np.float32)
    else:
        top = np.array(
            [random.randint(40, 150) for _ in range(3)], dtype=np.float32
        )
        bottom = np.array(
            [random.randint(130, 235) for _ in range(3)], dtype=np.float32
        )
        gradient = np.linspace(0, 1, height)[:, None, None]
        base = top * (1 - gradient) + bottom * gradient
        base = np.repeat(base, width, axis=1)

    noise = np.random.normal(0, random.uniform(3, 10), (height, width, 3))
    result = np.clip(base + noise, 0, 255).astype(np.uint8)
    if kind == "concrete":
        result = cv2.GaussianBlur(result, (5, 5), 0)
    return result


def _canvas_size(doc_width, doc_height, scenario):
    factor = 1.45
    if scenario == "far_away":
        factor = 2.15
    elif scenario == "close_up":
        factor = 1.05
    elif scenario in ("stacked_docs", "scattered_cards", "complex_bg"):
        factor = 1.75

    width = max(640, round(doc_width * factor))
    height = max(480, round(doc_height * factor))
    max_side = max(width, height)
    if max_side > 1900:
        scale = 1900 / max_side
        width, height = round(width * scale), round(height * scale)
    return width, height


def _placement_matrix(doc_width, doc_height, canvas_width, canvas_height, ratio, angle):
    fit_scale = min(canvas_width / doc_width, canvas_height / doc_height)
    scale = fit_scale * ratio
    new_width, new_height = doc_width * scale, doc_height * scale

    if new_width <= canvas_width:
        offset_x = random.uniform(0, canvas_width - new_width)
    else:
        offset_x = random.uniform(canvas_width - new_width, 0)
    if new_height <= canvas_height:
        offset_y = random.uniform(0, canvas_height - new_height)
    else:
        offset_y = random.uniform(canvas_height - new_height, 0)

    base = np.array([[scale, 0, offset_x], [0, scale, offset_y]], dtype=np.float64)
    center = (offset_x + new_width / 2, offset_y + new_height / 2)
    rotation = cv2.getRotationMatrix2D(center, angle, 1.0)
    affine = np.vstack([base, [0, 0, 1]])
    rotate3 = np.vstack([rotation, [0, 0, 1]])
    return (rotate3 @ affine)[:2]


def _move_matrix_center(matrix, doc_width, doc_height, target_x, target_y):
    box = project_bbox_affine((0, 0, doc_width, doc_height), matrix)
    current_x = (box[0] + box[2]) / 2
    current_y = (box[1] + box[3]) / 2
    moved = matrix.copy()
    moved[0, 2] += target_x - current_x
    moved[1, 2] += target_y - current_y
    return moved


def _warp_document(document, matrix, canvas_width, canvas_height, border_value):
    warped = cv2.warpAffine(
        document,
        matrix,
        (canvas_width, canvas_height),
        borderValue=border_value,
        flags=cv2.INTER_LINEAR,
    )
    mask = cv2.warpAffine(
        np.full(document.shape[:2], 255, dtype=np.uint8),
        matrix,
        (canvas_width, canvas_height),
        borderValue=0,
        flags=cv2.INTER_LINEAR,
    )
    return warped, mask


def _composite(background, foreground, mask):
    alpha = cv2.GaussianBlur(mask, (3, 3), 0).astype(np.float32)[:, :, None] / 255
    return (
        foreground.astype(np.float32) * alpha
        + background.astype(np.float32) * (1 - alpha)
    ).astype(np.uint8)


def _draw_fingers(image):
    height, width = image.shape[:2]
    boxes = []
    for _ in range(random.randint(1, 3)):
        edge = random.choice(["left", "right", "top", "bottom"])
        length = random.randint(round(min(width, height) * 0.18), round(min(width, height) * 0.38))
        thickness = random.randint(round(min(width, height) * 0.05), round(min(width, height) * 0.1))
        if edge == "left":
            start, end = (0, random.randint(0, height)), (length, random.randint(0, height))
        elif edge == "right":
            start, end = (width, random.randint(0, height)), (width - length, random.randint(0, height))
        elif edge == "top":
            start, end = (random.randint(0, width), 0), (random.randint(0, width), length)
        else:
            start, end = (random.randint(0, width), height), (random.randint(0, width), height - length)
        color = (
            random.randint(105, 155),
            random.randint(145, 190),
            random.randint(190, 235),
        )
        cv2.line(image, start, end, color, thickness, cv2.LINE_AA)
        radius = thickness // 2
        cv2.circle(image, end, radius, color, -1, cv2.LINE_AA)
        boxes.append(
            (
                min(start[0], end[0]) - radius,
                min(start[1], end[1]) - radius,
                max(start[0], end[0]) + radius,
                max(start[1], end[1]) + radius,
            )
        )
    return boxes


def _apply_paper_folds(image, strong=False):
    result = image.astype(np.float32)
    height, width = image.shape[:2]
    for _ in range(random.randint(2, 5 if strong else 3)):
        horizontal = random.random() < 0.5
        position = random.randint(
            round((height if horizontal else width) * 0.15),
            round((height if horizontal else width) * 0.85),
        )
        band = random.randint(2, 8)
        if horizontal:
            result[max(0, position - band):position + band] *= random.uniform(0.72, 0.9)
        else:
            result[:, max(0, position - band):position + band] *= random.uniform(0.72, 0.9)
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_thermal_fade(image):
    result = image.astype(np.float32)
    height, width = image.shape[:2]
    mask = np.zeros((height, width), dtype=np.float32)
    for _ in range(random.randint(3, 8)):
        center = (random.randint(0, width), random.randint(0, height))
        axes = (
            random.randint(max(15, width // 15), max(20, width // 3)),
            random.randint(max(15, height // 25), max(20, height // 6)),
        )
        strength = random.uniform(0.25, 0.75)
        patch = np.zeros_like(mask)
        cv2.ellipse(patch, center, axes, random.uniform(0, 180), 0, 360, strength, -1)
        mask = np.maximum(mask, cv2.GaussianBlur(patch, (0, 0), sigmaX=15))
    paper = np.full_like(result, (245, 245, 240), dtype=np.float32)
    return np.clip(result * (1 - mask[:, :, None]) + paper * mask[:, :, None], 0, 255).astype(np.uint8)


def apply_nonlinear_warp(image, boxes, strength=0.025):
    height, width = image.shape[:2]
    amplitude_x = width * strength
    amplitude_y = height * strength * 0.55
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    map_x = xx - amplitude_x * np.sin(2 * math.pi * yy / max(1, height))
    map_y = yy - amplitude_y * np.sin(2 * math.pi * xx / max(1, width))
    warped = cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    transformed_boxes = []
    for class_id, x1, y1, x2, y2 in boxes:
        xs = np.linspace(x1, x2, 8)
        ys = np.linspace(y1, y2, 8)
        points = np.array(
            [(x, y) for x in xs for y in (y1, y2)]
            + [(x, y) for y in ys for x in (x1, x2)],
            dtype=np.float32,
        )
        new_x = points[:, 0] + amplitude_x * np.sin(
            2 * math.pi * points[:, 1] / max(1, height)
        )
        new_y = points[:, 1] + amplitude_y * np.sin(
            2 * math.pi * points[:, 0] / max(1, width)
        )
        transformed_boxes.append(
            (
                class_id,
                float(new_x.min()),
                float(new_y.min()),
                float(new_x.max()),
                float(new_y.max()),
            )
        )
    return warped, transformed_boxes


def _apply_postprocessing(image, scenario):
    result = image
    height, width = result.shape[:2]
    if scenario == "dark_lighting":
        result = cv2.convertScaleAbs(result, alpha=random.uniform(0.42, 0.68), beta=random.randint(-25, -5))
    elif scenario == "bright_overexp":
        result = cv2.convertScaleAbs(result, alpha=random.uniform(1.3, 1.65), beta=random.randint(20, 50))
    elif scenario == "glare_reflection":
        overlay = result.astype(np.float32)
        center = (random.randint(0, width), random.randint(0, height))
        radius = random.randint(max(20, min(width, height) // 8), max(30, min(width, height) // 3))
        yy, xx = np.mgrid[0:height, 0:width]
        distance = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2)
        glare = np.clip(1 - distance / radius, 0, 1) ** 2 * random.uniform(100, 210)
        result = np.clip(overlay + glare[:, :, None], 0, 255).astype(np.uint8)
    elif scenario == "shadow_partial":
        mask = np.zeros((height, width), np.float32)
        points = np.int32(
            [[0, 0], [random.randint(width // 3, width), 0], [random.randint(0, width), height], [0, height]]
        )
        cv2.fillPoly(mask, [points], random.uniform(0.35, 0.65))
        mask = cv2.GaussianBlur(mask, (51, 51), 0)
        result = np.clip(result.astype(np.float32) * (1 - mask[:, :, None]), 0, 255).astype(np.uint8)
    elif scenario == "motion_blur":
        size = random.choice([7, 9, 11, 13])
        kernel = np.zeros((size, size), np.float32)
        kernel[size // 2] = 1 / size
        rotation = cv2.getRotationMatrix2D((size / 2, size / 2), random.uniform(0, 180), 1)
        kernel = cv2.warpAffine(kernel, rotation, (size, size))
        kernel /= max(kernel.sum(), 1e-6)
        result = cv2.filter2D(result, -1, kernel)
    elif scenario == "scan_artifact":
        result = cv2.convertScaleAbs(result, alpha=0.93, beta=10)
        for _ in range(random.randint(3, 8)):
            y = random.randint(0, height - 1)
            cv2.line(result, (0, y), (width, y), (190, 190, 190), random.choice([1, 1, 2]))

    if random.random() < 0.55:
        result = add_gaussian_noise(result, random.uniform(2, 8))
    if random.random() < 0.25:
        result = cv2.GaussianBlur(result, (3, 3), 0)
    if random.random() < 0.6:
        ok, encoded = cv2.imencode(
            ".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, random.randint(48, 88)]
        )
        if ok:
            result = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    return result


def apply_document_scenario(image, boxes, scenario=None, paper=False):
    if not boxes:
        raise ValueError("Minimal satu bbox dokumen diperlukan")
    if scenario is None:
        scenario = random.choice(SCENARIOS)

    document = image.copy()
    source_boxes = list(boxes)
    document_class = boxes[0][0]

    if scenario in ("paper_crumple", "folded"):
        document = _apply_paper_folds(document, strong=scenario == "folded")
    if scenario == "thermal_fade":
        document = apply_thermal_fade(document)
    if scenario == "rolled_warp":
        document, source_boxes = apply_nonlinear_warp(document, source_boxes, random.uniform(0.018, 0.045))
    if scenario == "damaged_card":
        for _ in range(random.randint(4, 12)):
            point1 = (random.randint(0, document.shape[1]), random.randint(0, document.shape[0]))
            point2 = (random.randint(0, document.shape[1]), random.randint(0, document.shape[0]))
            cv2.line(document, point1, point2, (185, 185, 185), random.choice([1, 1, 2]), cv2.LINE_AA)

    doc_height, doc_width = document.shape[:2]
    canvas_width, canvas_height = _canvas_size(doc_width, doc_height, scenario)
    background_kind = random.choice(["desk_wood", "cloth_dark", "cloth_light", "concrete", "gradient"])
    if scenario == "face_background":
        background_kind = "hand_skin"
    background = make_background(background_kind, canvas_width, canvas_height)
    background_boxes = []
    if scenario == "complex_bg":
        for _ in range(30):
            color = tuple(random.randint(20, 235) for _ in range(3))
            point1 = (random.randint(0, canvas_width), random.randint(0, canvas_height))
            point2 = (random.randint(0, canvas_width), random.randint(0, canvas_height))
            cv2.line(background, point1, point2, color, random.randint(1, 5))

    angle = random.uniform(-4, 4)
    ratio = random.uniform(0.68, 0.84)
    if scenario == "tilt_mild":
        angle = random.uniform(-10, 10)
    elif scenario == "tilt_strong":
        angle = random.uniform(-28, 28)
    elif scenario == "rotation_free":
        angle = random.uniform(-180, 180)
    elif scenario == "far_away":
        ratio = random.uniform(0.32, 0.5)
    elif scenario == "close_up":
        ratio = random.uniform(1.0, 1.2)
    elif scenario == "face_background":
        ratio = random.uniform(0.52, 0.64)

    border_value = paper_border_value() if paper else tuple(int(value) for value in document[0, 0])

    matrix = _placement_matrix(
        doc_width, doc_height, canvas_width, canvas_height, ratio, angle
    )
    if scenario == "face_background":
        portrait_width = max(150, round(canvas_width * random.uniform(0.24, 0.32)))
        portrait_height = min(
            max(190, round(portrait_width * random.uniform(1.15, 1.4))),
            canvas_height,
        )
        portrait, face_box = generate_synthetic_portrait(
            portrait_width, portrait_height
        )
        portrait_bgr = cv2.cvtColor(np.array(portrait), cv2.COLOR_RGB2BGR)
        main_box = project_bbox_affine((0, 0, doc_width, doc_height), matrix)
        main_center = (
            (main_box[0] + main_box[2]) / 2,
            (main_box[1] + main_box[3]) / 2,
        )
        candidates = [
            (0, 0),
            (canvas_width - portrait_width, 0),
            (0, canvas_height - portrait_height),
            (canvas_width - portrait_width, canvas_height - portrait_height),
        ]
        portrait_x, portrait_y = max(
            candidates,
            key=lambda point: (
                point[0] + portrait_width / 2 - main_center[0]
            ) ** 2
            + (
                point[1] + portrait_height / 2 - main_center[1]
            ) ** 2,
        )
        background[
            portrait_y:portrait_y + portrait_height,
            portrait_x:portrait_x + portrait_width,
        ] = portrait_bgr
        background_boxes.append(
            (
                4,
                portrait_x + face_box[0],
                portrait_y + face_box[1],
                portrait_x + face_box[2],
                portrait_y + face_box[3],
            )
        )
    projected = list(background_boxes)
    if scenario in ("stacked_docs", "scattered_cards"):
        extra_count = random.randint(1, 3 if scenario == "stacked_docs" else 2)
        main_box = project_bbox_affine((0, 0, doc_width, doc_height), matrix)
        main_center = (
            (main_box[0] + main_box[2]) / 2,
            (main_box[1] + main_box[3]) / 2,
        )
        corners = [
            (canvas_width * 0.18, canvas_height * 0.2),
            (canvas_width * 0.82, canvas_height * 0.2),
            (canvas_width * 0.18, canvas_height * 0.8),
            (canvas_width * 0.82, canvas_height * 0.8),
        ]
        random.shuffle(corners)
        for index in range(extra_count):
            extra_ratio = ratio * random.uniform(0.72, 0.95 if scenario == "stacked_docs" else 0.62)
            extra_angle = random.uniform(-22, 22 if scenario == "stacked_docs" else 48)
            extra_matrix = _placement_matrix(
                doc_width, doc_height, canvas_width, canvas_height, extra_ratio, extra_angle
            )
            if scenario == "scattered_cards":
                target = corners[index % len(corners)]
            else:
                direction = -1 if index % 2 else 1
                target = (
                    main_center[0] + direction * canvas_width * (0.08 + index * 0.035),
                    main_center[1] - direction * canvas_height * (0.07 + index * 0.025),
                )
            extra_matrix = _move_matrix_center(
                extra_matrix, doc_width, doc_height, target[0], target[1]
            )
            extra_warp, extra_mask = _warp_document(
                document, extra_matrix, canvas_width, canvas_height, border_value
            )
            background = _composite(background, extra_warp, extra_mask)
            extra_boxes = [
                (class_id, *project_bbox_affine((x1, y1, x2, y2), extra_matrix))
                for class_id, x1, y1, x2, y2 in source_boxes
            ]
            projected.extend(extra_boxes)

    warped, mask = _warp_document(
        document, matrix, canvas_width, canvas_height, border_value
    )
    canvas = _composite(background, warped, mask)
    main_boxes = [
        (class_id, *project_bbox_affine((x1, y1, x2, y2), matrix))
        for class_id, x1, y1, x2, y2 in source_boxes
    ]

    if projected:
        main_document = next(
            (box[1:] for box in main_boxes if box[0] == document_class), None
        )
        if main_document:
            projected = [
                box
                for box in projected
                if compute_visible_ratio(box[1:], [main_document])
                >= (
                    0.18
                    if box[0] == document_class
                    else 0.25
                    if scenario == "face_background" and box[0] == 4
                    else MIN_VISIBLE
                )
            ]
    projected.extend(main_boxes)

    if scenario == "finger_occlusion":
        occluders = _draw_fingers(canvas)
        projected = [
            box
            for box in projected
            if compute_visible_ratio(box[1:], occluders) >= MIN_VISIBLE
        ]

    if scenario == "perspective":
        source = np.float32(
            [[0, 0], [canvas_width, 0], [canvas_width, canvas_height], [0, canvas_height]]
        )
        dx, dy = canvas_width * 0.1, canvas_height * 0.1
        target = np.float32(
            [
                [random.uniform(0, dx), random.uniform(0, dy)],
                [canvas_width - random.uniform(0, dx), random.uniform(0, dy)],
                [canvas_width - random.uniform(0, dx), canvas_height - random.uniform(0, dy)],
                [random.uniform(0, dx), canvas_height - random.uniform(0, dy)],
            ]
        )
        perspective = cv2.getPerspectiveTransform(source, target)
        canvas = cv2.warpPerspective(
            canvas,
            perspective,
            (canvas_width, canvas_height),
            borderValue=border_value,
        )
        projected = [
            (class_id, *project_bbox_perspective((x1, y1, x2, y2), perspective))
            for class_id, x1, y1, x2, y2 in projected
        ]

    labels = boxes_to_yolo(
        projected, canvas_width, canvas_height, document_class=document_class
    )
    canvas = _apply_postprocessing(canvas, scenario)
    return canvas, labels, scenario


def save_yolo_sample(image, labels, image_path, label_path, quality=92):
    os.makedirs(os.path.dirname(image_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(label_path) or ".", exist_ok=True)
    if not cv2.imwrite(image_path, image, [cv2.IMWRITE_JPEG_QUALITY, quality]):
        raise OSError(f"Gagal menyimpan gambar: {image_path}")
    with open(label_path, "w", encoding="utf-8") as file:
        for class_id, xc, yc, width, height in labels:
            file.write(
                f"{class_id} {xc:.6f} {yc:.6f} {width:.6f} {height:.6f}\n"
            )


def write_data_yaml(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    names = "\n".join(f"  {class_id}: {name}" for class_id, name in CLASS_NAMES.items())
    content = f"""# PENTING: saat training YOLO gunakan fliplr=0.0.
# Mirror horizontal membuat teks, nomor identitas, nomor kartu, dan barcode tidak realistis.
# Contoh: model.train(data='data.yaml', fliplr=0.0)
path: {os.path.abspath(output_dir)}
train: images/train
val: images/val

nc: {len(CLASS_NAMES)}
names:
{names}
"""
    with open(os.path.join(output_dir, "data.yaml"), "w", encoding="utf-8") as file:
        file.write(content)


def generate_scenario_dataset(
    generator,
    output_dir,
    total_images,
    scenarios=None,
    val_split=0.15,
):
    for category in ("images", "labels"):
        for split in ("train", "val", "test"):
            directory = os.path.join(output_dir, category, split)
            if not os.path.isdir(directory):
                continue
            for filename in os.listdir(directory):
                path = os.path.join(directory, filename)
                if os.path.isfile(path):
                    os.remove(path)

    scenarios = scenarios or SCENARIOS
    validation_count = (
        max(1, round(total_images * val_split)) if total_images > 1 else 0
    )
    scenario_cycle = scenarios * (total_images // len(scenarios) + 1)
    random.shuffle(scenario_cycle)
    stats = {scenario: 0 for scenario in scenarios}

    for index in range(total_images):
        scenario = scenario_cycle[index]
        split = "val" if index < validation_count else "train"
        generator(
            os.path.join(output_dir, "images", split),
            os.path.join(output_dir, "labels", split),
            index,
            scenario=scenario,
        )
        stats[scenario] += 1
        if (index + 1) % max(1, total_images // 10) == 0:
            print(f"  [{index + 1}/{total_images}] scenario={scenario}")

    write_data_yaml(output_dir)
    print("\nDistribusi skenario:")
    for scenario, count in sorted(stats.items(), key=lambda item: -item[1]):
        print(f"  {scenario:20s}: {count}")
    print(f"Output: {os.path.abspath(output_dir)}")
    return stats
