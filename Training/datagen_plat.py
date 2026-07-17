import os
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datagen_common import (
    SCENARIOS,
    apply_document_scenario,
    fit_font,
    generate_scenario_dataset,
    load_font,
    save_yolo_sample,
    text_bbox,
)

OUTPUT_DIR = "datasets/plat_synth"
TOTAL_IMAGES = 1000


def generate_plat_mockup(output_path, label_path, img_idx, scenario=None):
    # 1. Setup Dimensi Canvas Plat Nomor (Standar ~ 460 x 140 mm proporsinya)
    width, height = 460, 150
    
    # Variasi Warna Plat Nomor di Indonesia
    tipe_plat = random.choice([
        {"bg": (20, 20, 20), "text": (245, 245, 245)},    # Hitam (Pribadi Lama)
        {"bg": (245, 245, 245), "text": (20, 20, 20)},    # Putih (Pribadi Baru)
        {"bg": (210, 30, 30), "text": (245, 245, 245)},   # Merah (Dinas/Pemerintah)
        {"bg": (230, 180, 20), "text": (20, 20, 20)},     # Kuning (Angkutan Umum)
        {"bg": (30, 120, 50), "text": (245, 245, 245)}    # Hijau (Kawasan Perdagangan Bebas)
    ])
    
    image = Image.new('RGB', (width, height), color=tipe_plat["bg"])
    draw = ImageDraw.Draw(image)
    
    # Load Font (Mencoba menggunakan font bold yang umum)
    font_tgl = load_font(30, bold=True)

    # 2. Generate Data Kombinasi Plat
    kode_wilayah = random.choice(["B", "D", "F", "L", "N", "W", "AG", "AD", "AB", "DK", "BK", "BP"])
    angka_plat = str(random.randint(1, 9999))
    
    # Generate 1-3 huruf acak di belakang
    huruf_belakang = "".join([random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(random.randint(1, 3))])
    teks_plat = f"{kode_wilayah} {angka_plat} {huruf_belakang}"
    
    # Masa Berlaku (Bulan . Tahun)
    bulan = str(random.randint(1, 12)).zfill(2)
    tahun = str(random.randint(24, 30))
    teks_tgl = f"{bulan} . {tahun}"
    font_plat = fit_font(draw, teks_plat, width - 35, 90, bold=True, min_size=42)

    # 3. Menggambar Elemen Plat
    # Garis tepi (Border) plat
    border_margin = 5
    draw.rectangle(
        [border_margin, border_margin, width-border_margin, height-border_margin], 
        outline=tipe_plat["text"], width=3
    )
    
    # Garis pemisah bawah (Opsional, biasa ada di plat cetakan lama)
    if random.random() > 0.5:
        draw.line((10, 110, width-10, 110), fill=tipe_plat["text"], width=2)

    # Teks Utama (Nomor Kendaraan)
    draw.text((width/2, 55), teks_plat, fill=tipe_plat["text"], font=font_plat, anchor="mm")
    plat_bbox = text_bbox(
        draw,
        (width / 2, 55),
        teks_plat,
        font_plat,
        anchor="mm",
        padding=5,
    )
    
    # Teks Masa Berlaku (Biasa di bawah tengah atau bawah kanan)
    tgl_x, tgl_y = width/2, 125
    draw.text((tgl_x, tgl_y), teks_tgl, fill=tipe_plat["text"], font=font_tgl, anchor="mm")
    expiry_bbox = text_bbox(
        draw,
        (tgl_x, tgl_y),
        teks_tgl,
        font_tgl,
        anchor="mm",
        padding=3,
    )

    # 5. Augmentasi Visual (Sangat penting untuk Plat Nomor di jalan)
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    boxes = [
        (5, 0, 0, width, height),
        (3, *plat_bbox),
        (3, *expiry_bbox),
    ]
    cv_img, yolo_labels, _ = apply_document_scenario(
        cv_img, boxes, scenario=scenario, paper=False
    )

    # 6. Ekspor Gambar dan Label YOLO
    save_yolo_sample(
        cv_img,
        yolo_labels,
        f"{output_path}/plat_synth_{img_idx}.jpg",
        f"{label_path}/plat_synth_{img_idx}.txt",
    )
    return cv_img, yolo_labels

if __name__ == "__main__":
    generate_scenario_dataset(
        generate_plat_mockup, OUTPUT_DIR, TOTAL_IMAGES, scenarios=SCENARIOS
    )
