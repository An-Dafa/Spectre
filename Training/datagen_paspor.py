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

# Inisialisasi Faker
fake = Faker('id_ID')
OUTPUT_DIR = "datasets/paspor_synth"
TOTAL_IMAGES = 900

def generate_paspor_mockup(output_path, label_path, img_idx, scenario=None):
    # 1. Setup Canvas Latar Belakang Paspor (Gradasi/Warna Ungu Muda kebiruan)
    width, height = 850, 600
    image = Image.new('RGB', (width, height), color=(225, 225, 235))
    draw = ImageDraw.Draw(image)
    
    # Elemen desain dasar paspor
    draw.rectangle([0, 500, width, 600], fill=(240, 240, 240)) # Area MRZ di bawah putih
    
    # Load Font
    font_header = load_font(22, bold=True)
    font_label = load_font(10)
    font_value = load_font(18)
    font_no_paspor = load_font(28, bold=True)
    font_mrz = load_font(24, mono=True)

    # 2. Generate Data Paspor
    nama_depan = fake.first_name().upper()
    nama_belakang = fake.last_name().upper()
    nama_lengkap = f"{nama_depan} {nama_belakang}"
    
    # Format No Paspor: 1 Huruf + 7 Angka
    huruf_awal = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    angka_paspor = f"{random.randint(1000000, 9999999)}"
    no_paspor = f"{huruf_awal} {angka_paspor}"
    
    jk = random.choice(["L/M", "P/F"])
    tempat_lahir = fake.city().upper()
    
    # Tanggal
    tgl_lahir_obj = fake.date_of_birth(minimum_age=1, maximum_age=70)
    tgl_lahir = tgl_lahir_obj.strftime("%d %b %Y").upper()
    tgl_keluar_obj = datetime.now() - timedelta(days=random.randint(100, 1000))
    tgl_keluar = tgl_keluar_obj.strftime("%d %b %Y").upper()
    tgl_habis = (tgl_keluar_obj + timedelta(days=10*365)).strftime("%d %b %Y").upper()
    
    kantor = f"KANTOR IMIGRASI KELAS I {fake.city().upper()}"
    
    # Generate String MRZ (2 baris x 44 karakter)
    mrz_nama = f"{nama_belakang}<<{nama_depan}".ljust(39, '<')[:39]
    mrz_line1 = f"P<IDN{mrz_nama}"
    mrz_line2 = f"{huruf_awal}{angka_paspor}<0IDN{tgl_lahir_obj.strftime('%y%m%d')}0{jk[0]}<<<<<<<<<<<<<<<00"

    # 3. Menggambar Teks & Layout
    # Header
    draw.text((width/2, 20), "REPUBLIK INDONESIA", fill=(50, 50, 150), font=font_header, anchor="mm")
    draw.text((width/2, 45), "REPUBLIC OF INDONESIA", fill=(50, 50, 150), font=font_label, anchor="mm")
    
    # Label Kiri Atas
    draw.text((30, 30), "PASPOR", fill=(50, 50, 150), font=font_header)
    draw.text((30, 55), "PASSPORT", fill=(50, 50, 150), font=font_label)

    # Area Pas Foto
    face_w, face_h = 200, 260
    face_x, face_y = 40, 120
    portrait, face_bbox = generate_synthetic_portrait(face_w, face_h)
    image.paste(portrait, (face_x, face_y))

    # Kolom Data
    start_x = 280
    
    # Jenis, Kode Negara, No Paspor
    draw.text((start_x, 90), "Jenis / Type\nP", fill="black", font=font_label)
    draw.text((400, 90), "Kode Negara / Country Code\nIDN", fill="black", font=font_label)
    
    no_paspor_x, no_paspor_y = 620, 90
    draw.text((no_paspor_x, no_paspor_y), "No. Paspor / Passport No.", fill=(50, 50, 150), font=font_label)
    draw.text((no_paspor_x, no_paspor_y + 15), no_paspor, fill="black", font=font_no_paspor)
    no_paspor_bbox = text_bbox(
        draw,
        (no_paspor_x, no_paspor_y + 15),
        no_paspor,
        font_no_paspor,
        padding=4,
    )
    sensitive_boxes = [(3, *no_paspor_bbox)]

    # Baris Nama Lengkap
    draw.text((start_x, 150), "Nama Lengkap / Full Name", fill=(50, 50, 150), font=font_label)
    font_nama = fit_font(draw, nama_lengkap, width - start_x - 25, 18)
    name_xy = (start_x, 165)
    draw.text(name_xy, nama_lengkap, fill="black", font=font_nama)
    sensitive_boxes.append(
        (3, *text_bbox(draw, name_xy, nama_lengkap, font_nama))
    )

    # Kewarganegaraan
    draw.text((start_x, 210), "Kewarganegaraan / Nationality", fill=(50, 50, 150), font=font_label)
    nationality_xy = (start_x, 225)
    draw.text(nationality_xy, "INDONESIA", fill="black", font=font_value)
    sensitive_boxes.append(
        (3, *text_bbox(draw, nationality_xy, "INDONESIA", font_value))
    )

    # Tempat / Tgl Lahir / Kelamin
    draw.text((start_x, 270), "Tgl. Lahir / Date of Birth", fill=(50, 50, 150), font=font_label)
    birth_date_xy = (start_x, 285)
    draw.text(birth_date_xy, tgl_lahir, fill="black", font=font_value)
    sensitive_boxes.append(
        (3, *text_bbox(draw, birth_date_xy, tgl_lahir, font_value))
    )
    
    draw.text((500, 270), "Kelamin / Sex", fill=(50, 50, 150), font=font_label)
    sex_xy = (500, 285)
    draw.text(sex_xy, jk, fill="black", font=font_value)
    sensitive_boxes.append((3, *text_bbox(draw, sex_xy, jk, font_value)))

    draw.text((start_x, 330), "Tempat Lahir / Place of Birth", fill=(50, 50, 150), font=font_label)
    birth_place_xy = (start_x, 345)
    draw.text(birth_place_xy, tempat_lahir, fill="black", font=font_value)
    sensitive_boxes.append(
        (3, *text_bbox(draw, birth_place_xy, tempat_lahir, font_value))
    )

    # Tgl Pengeluaran & Habis Berlaku
    draw.text((start_x, 390), "Tgl. Pengeluaran / Date of Issue", fill=(50, 50, 150), font=font_label)
    issue_xy = (start_x, 405)
    draw.text(issue_xy, tgl_keluar, fill="black", font=font_value)
    sensitive_boxes.append(
        (3, *text_bbox(draw, issue_xy, tgl_keluar, font_value))
    )

    draw.text((550, 390), "Tgl. Habis Berlaku / Date of Expiry", fill=(50, 50, 150), font=font_label)
    expiry_xy = (550, 405)
    draw.text(expiry_xy, tgl_habis, fill="black", font=font_value)
    sensitive_boxes.append(
        (3, *text_bbox(draw, expiry_xy, tgl_habis, font_value))
    )

    # Kantor
    draw.text((550, 450), "Kantor yang mengeluarkan / Issuing Office", fill=(50, 50, 150), font=font_label)
    font_kantor = fit_font(draw, kantor, width - 565, 18, min_size=9)
    office_xy = (550, 465)
    draw.text(office_xy, kantor, fill="black", font=font_kantor)
    sensitive_boxes.append(
        (3, *text_bbox(draw, office_xy, kantor, font_kantor))
    )

    # MRZ Area
    mrz1_xy, mrz2_xy = (20, 520), (20, 560)
    draw.text(mrz1_xy, mrz_line1, fill="black", font=font_mrz)
    draw.text(mrz2_xy, mrz_line2, fill="black", font=font_mrz)
    sensitive_boxes.append(
        (3, *text_bbox(draw, mrz1_xy, mrz_line1, font_mrz, padding=2))
    )
    sensitive_boxes.append(
        (3, *text_bbox(draw, mrz2_xy, mrz_line2, font_mrz, padding=2))
    )

    # 5. Augmentasi Visual
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    boxes = [
        (2, 0, 0, width, height),
        *sensitive_boxes,
        (
            4,
            face_x + face_bbox[0],
            face_y + face_bbox[1],
            face_x + face_bbox[2],
            face_y + face_bbox[3],
        ),
    ]
    cv_img, yolo_labels, _ = apply_document_scenario(
        cv_img, boxes, scenario=scenario, paper=True
    )

    # 6. Simpan Gambar & Label
    save_yolo_sample(
        cv_img,
        yolo_labels,
        f"{output_path}/paspor_synth_{img_idx}.jpg",
        f"{label_path}/paspor_synth_{img_idx}.txt",
    )
    return cv_img, yolo_labels

if __name__ == "__main__":
    generate_scenario_dataset(
        generate_paspor_mockup, OUTPUT_DIR, TOTAL_IMAGES, scenarios=SCENARIOS
    )
