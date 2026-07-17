import os
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from faker import Faker
from datetime import datetime, timedelta
from datagen_common import (
    SCENARIOS,
    apply_document_scenario,
    fit_font,
    generate_synthetic_portrait,
    generate_scenario_dataset,
    load_font,
    save_yolo_sample,
    text_bbox,
)

# Inisialisasi Faker untuk data Indonesia
fake = Faker('id_ID')
OUTPUT_DIR = "datasets/sim_synth"
TOTAL_IMAGES = 900


def draw_qr_placeholder(draw, box):
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill="white", outline="black", width=2)
    cells = random.choice([11, 13, 15])
    cell = min((x2 - x1 - 8) // cells, (y2 - y1 - 8) // cells)
    offset_x = x1 + ((x2 - x1) - cell * cells) // 2
    offset_y = y1 + ((y2 - y1) - cell * cells) // 2
    matrix = [[random.random() < 0.48 for _ in range(cells)] for _ in range(cells)]
    for finder_y, finder_x in ((0, 0), (0, cells - 5), (cells - 5, 0)):
        for row in range(5):
            for column in range(5):
                matrix[finder_y + row][finder_x + column] = (
                    row in (0, 4)
                    or column in (0, 4)
                    or (1 < row < 4 and 1 < column < 4)
                )
    for row in range(cells):
        for column in range(cells):
            if matrix[row][column]:
                px = offset_x + column * cell
                py = offset_y + row * cell
                draw.rectangle((px, py, px + cell, py + cell), fill="black")


def draw_fingerprint(draw, box):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(
        box,
        radius=8,
        fill=(215, 215, 215),
        outline=(90, 90, 90),
        width=1,
    )
    for index in range(random.randint(8, 13)):
        margin_x = 4 + index * 2
        margin_y = 5 + index * 3
        if x1 + margin_x >= x2 - margin_x or y1 + margin_y >= y2 - margin_y:
            break
        draw.arc(
            (x1 + margin_x, y1 + margin_y, x2 - margin_x, y2 - margin_y),
            random.randint(185, 220),
            random.randint(500, 535),
            fill=(65, 65, 65),
            width=1,
        )
    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
    draw.arc(
        (center_x - 12, center_y - 20, center_x + 12, center_y + 20),
        70,
        290,
        fill=(45, 45, 45),
        width=2,
    )


def generate_sim_mockup(
    output_path,
    label_path,
    img_idx,
    scenario=None,
    security_feature=None,
):
    # 1. Setup Canvas Kertas/Latar Belakang SIM (Putih Tulang)
    width, height = 800, 500
    image = Image.new('RGB', (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    
    # Header Merah khas SIM Indonesia
    draw.rectangle([0, 0, width, 100], fill=(210, 30, 30))
    
    # Load Font (Gunakan fallback default jika arial tidak ada)
    font_header_id = load_font(36, bold=True)
    font_header_en = load_font(18)
    font_sim_type = load_font(70, bold=True)
    font_label = load_font(16)
    font_value = load_font(18, bold=True)
    font_no_sim = load_font(26, bold=True)

    # 2. Generate Data via Faker
    tipe_sim = random.choice(["A", "B1", "B2", "C", "C1", "C2", "C3", "D", "D1"])
    # Nomor SIM Indonesia format: 4 digit - 4 digit - 6 digit
    no_sim = f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"
    nama = fake.name().upper()
    tempat_lahir = fake.city().upper()
    tgl_lahir = fake.date_of_birth(minimum_age=17, maximum_age=65).strftime("%d-%m-%Y")
    gol_darah = random.choice(["A", "B", "O", "AB", "-"])
    jk = random.choice(["PRIA", "WANITA"])
    alamat = fake.street_address().upper()
    kota = fake.city().upper()
    pekerjaan = random.choice(["KARYAWAN SWASTA", "WIRASWASTA", "MAHASISWA", "PNS", "MENGURUS RUMAH TANGGA"])
    
    # Tanggal berlaku (5 tahun dari pembuatan)
    tgl_buat = datetime.now()
    tgl_berlaku = (tgl_buat + timedelta(days=5*365)).strftime("%d-%m-%Y")

    # 3. Menggambar Teks & Layout
    # Teks Header
    draw.text((width/2, 20), "INDONESIA", fill="white", font=font_header_id, anchor="mm")
    draw.text((width/2, 50), "SURAT IZIN MENGEMUDI", fill="white", font=font_header_en, anchor="mm")
    draw.text((width/2, 75), "DRIVING LICENSE", fill="white", font=font_header_en, anchor="mm")
    
    # Kotak Golongan SIM (Kanan Atas)
    draw.rectangle([650, 10, 750, 90], fill="white", outline="black", width=2)
    draw.text((700, 50), tipe_sim, fill="black", font=font_sim_type, anchor="mm")
    type_bbox = text_bbox(
        draw, (700, 50), tipe_sim, font_sim_type, anchor="mm", padding=4
    )

    # Area Foto (Kiri) -> X: 40, Y: 150, W: 180, H: 220
    portrait, face_bbox = generate_synthetic_portrait(180, 220)
    image.paste(portrait, (40, 150))

    # Data Pemilik SIM (Tengah ke Kanan)
    start_x_label = 250
    start_x_value = 250
    start_y = 130
    line_spacing = 35

    labels = ["1. Nama", "2. Tempat, Tgl Lahir", "3. Gol. Darah", "4. Alamat", "5. Pekerjaan", "6. No. SIM"]
    values = [
        nama, 
        f"{tempat_lahir}, {tgl_lahir}", 
        f"{gol_darah}                         Jenis Kelamin : {jk}", 
        f"{alamat}\n{kota}", 
        pekerjaan, 
        "" # No SIM digambar terpisah agar font lebih besar
    ]

    sensitive_boxes = [(3, *type_bbox)]
    for i, (lbl, val) in enumerate(zip(labels, values)):
        y_pos = start_y + (i * line_spacing)
        # Khusus alamat beri spasi lebih karena bisa 2 baris
        if i >= 4: y_pos += 20
        if i >= 5: y_pos += 20
        
        draw.text((start_x_label, y_pos), lbl, fill="black", font=font_label)
        row_font = fit_font(
            draw,
            max(val.splitlines(), key=len, default=""),
            355,
            18,
            bold=True,
            min_size=10,
        )
        value_xy = (start_x_value, y_pos + 15)
        draw.text(value_xy, val, fill="black", font=row_font)
        if val:
            sensitive_boxes.append(
                (3, *text_bbox(draw, value_xy, val, row_font))
            )

    # Menggambar No SIM
    no_sim_y = 360
    draw.text((start_x_value, no_sim_y), no_sim, fill="black", font=font_no_sim)
    no_sim_bbox = text_bbox(
        draw, (start_x_value, no_sim_y), no_sim, font_no_sim, padding=4
    )
    sensitive_boxes.append((3, *no_sim_bbox))
    
    # Setiap sampel memakai tepat satu fitur tambahan.
    security_feature = security_feature or random.choice(
        ["qr", "fingerprint", "ghost_portrait"]
    )
    if security_feature not in {"qr", "fingerprint", "ghost_portrait"}:
        raise ValueError(f"Fitur keamanan SIM tidak dikenal: {security_feature}")

    extra_face_boxes = []
    if security_feature == "qr":
        qr_box = (665, 135, 765, 235)
        draw_qr_placeholder(draw, qr_box)
        sensitive_boxes.append((3, *qr_box))
    elif security_feature == "fingerprint":
        fingerprint_box = (690, 170, 770, 310)
        draw_fingerprint(draw, fingerprint_box)
        sensitive_boxes.append((3, *fingerprint_box))
    else:
        ghost_x, ghost_y, ghost_w, ghost_h = 655, 175, 105, 130
        ghost = portrait.resize((ghost_w, ghost_h)).convert("L").convert("RGB")
        ghost = Image.blend(
            Image.new("RGB", (ghost_w, ghost_h), (205, 215, 220)),
            ghost,
            0.42,
        )
        image.paste(ghost, (ghost_x, ghost_y))
        extra_face_boxes.append(
            (
                4,
                ghost_x + face_bbox[0] * ghost_w / 180,
                ghost_y + face_bbox[1] * ghost_h / 220,
                ghost_x + face_bbox[2] * ghost_w / 180,
                ghost_y + face_bbox[3] * ghost_h / 220,
            )
        )

    draw.text((670, 420), "Tanda Tangan", fill="black", font=font_label, anchor="mm")
    for _ in range(5): # Simulasi coretan tanda tangan
        x1, y1 = random.randint(620, 650), random.randint(390, 410)
        x2, y2 = random.randint(690, 720), random.randint(390, 410)
        draw.line((x1, y1, x2, y2), fill="black", width=2)

    # Berlaku s/d
    validity_text = f"Berlaku s/d : {tgl_berlaku}"
    validity_xy = (start_x_value, 420)
    draw.text(validity_xy, validity_text, fill="black", font=font_value)
    sensitive_boxes.append(
        (3, *text_bbox(draw, validity_xy, validity_text, font_value))
    )

    # 5. Augmentasi Visual untuk Track A (Edge Vision)
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    boxes = [
        (1, 0, 0, width, height),
        *sensitive_boxes,
        (
            4,
            40 + face_bbox[0],
            150 + face_bbox[1],
            40 + face_bbox[2],
            150 + face_bbox[3],
        ),
        *extra_face_boxes,
    ]
    cv_img, yolo_labels, _ = apply_document_scenario(
        cv_img, boxes, scenario=scenario, paper=False
    )

    # 6. Ekspor Gambar dan Label YOLO
    save_yolo_sample(
        cv_img,
        yolo_labels,
        f"{output_path}/sim_synth_{img_idx}.jpg",
        f"{label_path}/sim_synth_{img_idx}.txt",
    )
    return cv_img, yolo_labels

if __name__ == "__main__":
    generate_scenario_dataset(
        generate_sim_mockup, OUTPUT_DIR, TOTAL_IMAGES, scenarios=SCENARIOS
    )
