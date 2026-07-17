import os
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from faker import Faker
from datetime import datetime
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

# Inisialisasi Faker dengan bahasa Indonesia
fake = Faker('id_ID')
OUTPUT_DIR = "datasets/ktp_synth"
TOTAL_IMAGES = 800

def generate_ktp_mockup(output_path, label_path, img_idx, scenario=None):
    # 1. Buat Background (Simulasi kartu KTP biru)
    width, height = 800, 500
    image = Image.new('RGB', (width, height), color=(173, 216, 230))
    draw = ImageDraw.Draw(image)
    
    # Load Font (Pastikan ada arial.ttf / arialbd.ttf di sistem, atau gunakan default)
    font_header = load_font(22, bold=True)
    font_nik = load_font(36, bold=True)
    font_label = load_font(18)
    font_value = load_font(18)

    # 2. Generate Data Kependudukan via Faker
    provinsi = fake.state().upper()
    kota = fake.city().upper()
    nik = "".join([str(random.randint(0, 9)) for _ in range(16)])
    nama = fake.name().upper()
    tempat_lahir = fake.city().upper()
    tgl_lahir = fake.date_of_birth(minimum_age=17, maximum_age=65).strftime("%d-%m-%Y")
    jk = random.choice(["LAKI-LAKI", "PEREMPUAN"])
    gol_darah = random.choice(["A", "B", "O", "AB", "-"])
    alamat = fake.street_address().upper()
    rt_rw = f"{random.randint(1,99):03d}/{random.randint(1,99):03d}"
    kel_desa = fake.city_name().upper()
    kecamatan = fake.city_name().upper()
    agama = random.choice(["ISLAM", "KRISTEN", "KATHOLIK", "HINDU", "BUDDHA", "KONGHUCU"])
    status = random.choice(["BELUM KAWIN", "KAWIN", "CERAI HIDUP", "CERAI MATI"])
    pekerjaan = random.choice(["PELAJAR/MAHASISWA", "WIRASWASTA", "KARYAWAN SWASTA", "PNS"])

    # 3. Gambar Teks pada Gambar (Sesuai Layout KTP Asli)
    # Header
    draw.text((width/2, 30), f"PROVINSI {provinsi}", fill="black", font=font_header, anchor="mm")
    draw.text((width/2, 60), kota, fill="black", font=font_header, anchor="mm")

    # Baris NIK
    draw.text((40, 110), "NIK", fill="black", font=font_nik)
    nik_text = f": {nik}"
    draw.text((180, 110), nik_text, fill="black", font=font_nik)
    nik_bbox = text_bbox(draw, (180, 110), nik_text, font_nik, padding=5)
    sensitive_boxes = [(3, *nik_bbox)]

    # Kolom Label Kiri
    labels = [
        "Nama", "Tempat/Tgl Lahir", "Jenis kelamin", "Alamat", 
        "    RT/RW", "    Kel/Desa", "    Kecamatan", "Agama", 
        "Status Perkawinan", "Pekerjaan", "Kewarganegaraan", "Berlaku Hingga"
    ]
    
    # Kolom Value Kanan
    values = [
        f": {nama}", f": {tempat_lahir}, {tgl_lahir}", f": {jk}             Gol. Darah   : {gol_darah}", f": {alamat}",
        f": {rt_rw}", f": {kel_desa}", f": {kecamatan}", f": {agama}",
        f": {status}", f": {pekerjaan}", ": WNI", ": SEUMUR HIDUP"
    ]
    
    start_y = 170
    line_spacing = 25
    for i, (lbl, val) in enumerate(zip(labels, values)):
        draw.text((40, start_y + i*line_spacing), lbl, fill="black", font=font_label)
        row_font = fit_font(draw, val, 305, 18, min_size=10)
        value_xy = (230, start_y + i * line_spacing)
        draw.text(value_xy, val, fill="black", font=row_font)
        sensitive_boxes.append((3, *text_bbox(draw, value_xy, val, row_font)))
        
    # Area Pas Foto
    portrait, face_bbox = generate_synthetic_portrait(170, 200)
    image.paste(portrait, (550, 150))
    
    # Area Tanda Tangan
    tgl_buat = datetime.now().strftime("%d-%m-%Y")
    city_xy, date_xy = (635, 360), (635, 380)
    draw.text(city_xy, kota, fill="black", font=font_label, anchor="mm")
    draw.text(date_xy, tgl_buat, fill="black", font=font_label, anchor="mm")
    sensitive_boxes.append(
        (3, *text_bbox(draw, city_xy, kota, font_label, anchor="mm"))
    )
    sensitive_boxes.append(
        (3, *text_bbox(draw, date_xy, tgl_buat, font_label, anchor="mm"))
    )
    
    # Simulasi Tanda Tangan Acak (Garis-garis)
    for _ in range(6):
        x1, y1 = random.randint(580, 620), random.randint(400, 420)
        x2, y2 = random.randint(650, 690), random.randint(420, 450)
        draw.line((x1, y1, x2, y2), fill="black", width=3)

    # 4. Tambahkan Augmentasi Visual (Untuk Edge Vision Robustness)
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    boxes = [
        (0, 0, 0, width, height),
        *sensitive_boxes,
        (
            4,
            550 + face_bbox[0],
            150 + face_bbox[1],
            550 + face_bbox[2],
            150 + face_bbox[3],
        ),
    ]
    cv_img, yolo_labels, _ = apply_document_scenario(
        cv_img, boxes, scenario=scenario, paper=False
    )

    # 5. Ekspor Gambar dan Anotasi YOLO
    save_yolo_sample(
        cv_img,
        yolo_labels,
        f"{output_path}/ktp_synth_{img_idx}.jpg",
        f"{label_path}/ktp_synth_{img_idx}.txt",
    )
    return cv_img, yolo_labels

# Eksekusi Generator
if __name__ == "__main__":
    generate_scenario_dataset(
        generate_ktp_mockup, OUTPUT_DIR, TOTAL_IMAGES, scenarios=SCENARIOS
    )
