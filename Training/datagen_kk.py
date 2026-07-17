#!/usr/bin/env python3
"""
PrivAI - Synthetic Data Generator: Kartu Keluarga (KK)
========================================================
Class ID baru: 6 = kk, plus reuse class 3 = nik_teks (no wajah/class 4).
Kompatibel dengan skema label KTP/SIM/Paspor/Plat Nomor (class 0-5) yang sudah ada.

nc: 9
0 = ktp
1 = sim
2 = paspor
3 = nik_teks
4 = wajah
5 = plat_nomor
6 = kk
7 = kartu_atm   (reserved, generator terpisah)
8 = resi        (reserved, generator terpisah)

PENTING (training):
  Saat training YOLO dengan dataset ini, set augmentasi fliplr=0.0
  (jangan mirror horizontal) karena teks/angka NIK/no.KK akan jadi
  terbalik dan tidak representatif terhadap dokumen asli.
  Contoh: model.train(..., fliplr=0.0)

Standalone file - tidak butuh import eksternal selain library umum.
"""

import os
import io
import math
import json
import random
import string
import datetime

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =====================================================================
# KONFIGURASI
# =====================================================================
OUTPUT_DIR   = "datasets/kk_synth"
TOTAL_IMAGES = 1000
MIN_VISIBLE  = 0.5          # threshold visibility utk stacked/occlusion
SEED         = None         # set int utk reproducibility, None = random

# Dimensi dokumen KK - A4 landscape (proporsi ~1.414:1)
KK_W, KK_H = 1240, 877

# Class IDs (JANGAN diubah - kompatibel dgn dataset lama)
CLASS_KTP        = 0
CLASS_SIM        = 1
CLASS_PASPOR     = 2
CLASS_NIK_TEKS   = 3
CLASS_WAJAH      = 4
CLASS_PLAT_NOMOR = 5
CLASS_KK         = 6
CLASS_KARTU_ATM  = 7
CLASS_RESI       = 8

CLASS_NAMES = {
    0: "ktp", 1: "sim", 2: "paspor", 3: "nik_teks", 4: "wajah",
    5: "plat_nomor", 6: "kk", 7: "kartu_atm", 8: "resi",
}

# 18 skenario dasar + skenario khusus dokumen kertas (KK)
SCENARIOS = [
    "normal", "tilt_mild", "tilt_strong", "far_away", "close_up",
    "perspective", "finger_occlusion", "stacked_docs", "scattered_cards",
    "face_background", "dark_lighting", "bright_overexp", "glare_reflection",
    "shadow_partial", "motion_blur", "rotation_free", "damaged_card",
    "complex_bg", "paper_crumple", "scan_artifact",
]

BACKGROUNDS = [
    "desk_wood", "desk_white", "cloth_dark", "cloth_light",
    "hand_skin", "concrete", "gradient", "noise_paper",
]

if SEED is not None:
    random.seed(SEED)
    np.random.seed(SEED)

# =====================================================================
# FONT FALLBACK BERTINGKAT
# =====================================================================
_FONT_CANDIDATES_REGULAR = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
_FONT_CANDIDATES_BOLD = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]

_font_cache = {}


def get_font(size=16, bold=False):
    """Font fallback bertingkat:
    1) truetype sistem (DejaVu / Liberation)
    2) ImageFont.load_default(size=N)  (Pillow >= 10)
    3) ImageFont.load_default()        (tanpa argumen, Pillow lama)
    """
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    candidates = _FONT_CANDIDATES_BOLD if bold else _FONT_CANDIDATES_REGULAR
    font = None
    for path in candidates:
        try:
            if os.path.exists(path):
                font = ImageFont.truetype(path, size=size)
                break
        except Exception:
            continue

    if font is None:
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

    _font_cache[key] = font
    return font


# =====================================================================
# GEOMETRY HELPERS - bbox projection akurat
# =====================================================================
def project_bbox_to_canvas(bbox_xyxy, M):
    """Proyeksikan bbox axis-aligned (x1,y1,x2,y2) melalui matriks transform
    2x3 (affine, misal dari cv2.getRotationMatrix2D atau warpAffine chain)
    dengan menghitung 4 sudut lalu ambil bounding box dari titik-titik
    hasil transform. Ini WAJIB dipakai, bukan menormalkan bbox lama secara
    langsung, karena rotasi/scale membuat axis-aligned box lama tidak lagi
    valid untuk konten yang sudah dirotasi.

    bbox_xyxy : (x1, y1, x2, y2) dalam koordinat sumber
    M         : matriks affine 2x3 (numpy array) sumber -> tujuan
    return    : (x1, y1, x2, y2) dalam koordinat tujuan
    """
    x1, y1, x2, y2 = bbox_xyxy
    corners = np.array([
        [x1, y1, 1.0],
        [x2, y1, 1.0],
        [x2, y2, 1.0],
        [x1, y2, 1.0],
    ]).T  # shape (3,4)

    transformed = M @ corners  # shape (2,4)
    xs = transformed[0, :]
    ys = transformed[1, :]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def clip_bbox(bbox_xyxy, w, h):
    x1, y1, x2, y2 = bbox_xyxy
    x1 = max(0, min(x1, w))
    y1 = max(0, min(y1, h))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))
    return x1, y1, x2, y2


def bbox_area(bbox_xyxy):
    x1, y1, x2, y2 = bbox_xyxy
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def bbox_intersection(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return None
    return (ix1, iy1, ix2, iy2)


def xyxy_to_yolo(bbox_xyxy, img_w, img_h):
    x1, y1, x2, y2 = bbox_xyxy
    cx = (x1 + x2) / 2.0 / img_w
    cy = (y1 + y2) / 2.0 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return cx, cy, w, h


# =====================================================================
# VISIBILITY CHECK (level modul - WAJIB, bukan nested di generate_sample)
# =====================================================================
def compute_visible_ratio(target_rect, occluder_rects):
    """Hitung rasio area target_rect yang MASIH terlihat (tidak tertutup
    gabungan occluder_rects). Menggunakan pendekatan grid-sampling agar
    robust terhadap overlap ganda antar occluder tanpa perlu polygon
    union yang rumit.

    target_rect    : (x1,y1,x2,y2)
    occluder_rects : list of (x1,y1,x2,y2)
    return         : float 0.0 - 1.0
    """
    x1, y1, x2, y2 = target_rect
    area = bbox_area(target_rect)
    if area <= 0:
        return 0.0
    if not occluder_rects:
        return 1.0

    # grid sampling resolusi cukup untuk akurasi bbox-level (bukan pixel-mask)
    GRID = 20
    xs = np.linspace(x1, x2, GRID)
    ys = np.linspace(y1, y2, GRID)
    total = GRID * GRID
    covered = 0
    for gy in ys:
        for gx in xs:
            for (ox1, oy1, ox2, oy2) in occluder_rects:
                if ox1 <= gx <= ox2 and oy1 <= gy <= oy2:
                    covered += 1
                    break
    visible_ratio = 1.0 - (covered / total)
    return max(0.0, min(1.0, visible_ratio))


# =====================================================================
# DATA POOLS - sintetis, tidak menyerupai data nyata
# =====================================================================
NAMA_DEPAN = [
    "Eri", "Agus", "Budi", "Citra", "Dewi", "Siti", "Rudi", "Wawan",
    "Fitri", "Andi", "Bambang", "Sri", "Hendra", "Yuli", "Dedi", "Rina",
    "Slamet", "Ani", "Joko", "Wati", "Kurniawan", "Setiawan", "Wulandari",
    "Pratama", "Saputra", "Utami", "Kusuma", "Nugroho", "Handayani",
]
NAMA_BELAKANG = [
    "Kurniawan", "Wulansari", "Fawwaz", "Santoso", "Wijaya", "Purnama",
    "Setiawan", "Hidayat", "Rahayu", "Susanto", "Permana", "Lestari",
    "Firmansyah", "Ramadhan", "Anggraini", "Saputro", "", "", "",
]
GELAR = ["", "", "", "", "ST", "SE", "SPD", "SH", "S.Kom", "Amd"]

TEMPAT_LAHIR = [
    "PURBALINGGA", "BANTUL", "YOGYAKARTA", "SLEMAN", "JAKARTA", "SURABAYA",
    "BANDUNG", "SEMARANG", "MALANG", "SOLO", "KEDIRI", "MADIUN", "KLATEN",
    "PURWOKERTO", "CILACAP", "MAGELANG", "TEGAL", "PEKALONGAN",
]

AGAMA = ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDHA", "KONGHUCU"]

PENDIDIKAN = [
    "TIDAK/BLM SEKOLAH", "BELUM TAMAT SD", "TAMAT SD", "SLTP",
    "SLTA", "DIPLOMA I/II", "DIPLOMA III/SARJANA MUDA",
    "DIPLOMA IV/STRATA I", "STRATA II", "STRATA III",
]

PEKERJAAN = [
    "BELUM/TIDAK BEKERJA", "MENGURUS RUMAH TANGGA", "PELAJAR/MAHASISWA",
    "KARYAWAN SWASTA", "WIRASWASTA", "PNS", "DOKTER", "GURU",
    "PETANI/PEKEBUN", "PEDAGANG", "BURUH HARIAN LEPAS", "TNI", "POLRI",
    "KARYAWAN BUMN", "PERAWAT", "SOPIR",
]

STATUS_KAWIN = ["KAWIN", "BELUM KAWIN", "CERAI HIDUP", "CERAI MATI"]

KEWARGANEGARAAN = ["WNI", "WNI", "WNI", "WNI", "WNA"]

DESA_POOL = [
    "SENDANGTIRTO", "BANGUNTAPAN", "CONDONGCATUR", "SINDUADI",
    "TAMANTIRTO", "MARGOAGUNG", "SUMBERAGUNG", "WEDOMARTANI",
]
KECAMATAN_POOL = [
    "BERBAH", "BANGUNTAPAN", "DEPOK", "MLATI", "KASIHAN", "GAMPING",
    "NGAGLIK", "PIYUNGAN",
]
KABUPATEN_POOL = [
    "SLEMAN", "BANTUL", "KULON PROGO", "GUNUNG KIDUL", "KOTA YOGYAKARTA",
]
PROVINSI_POOL = [
    "DAERAH ISTIMEWA YOGYAKARTA", "JAWA TENGAH", "JAWA TIMUR", "JAWA BARAT",
]


def gen_nik():
    """NIK 16 digit format acak (bukan NIK asli, tidak divalidasi terhadap
    struktur wilayah resmi)."""
    return "".join(random.choices(string.digits, k=16))


def gen_no_kk():
    return "".join(random.choices(string.digits, k=16))


def gen_nama():
    depan = random.choice(NAMA_DEPAN)
    belakang = random.choice(NAMA_BELAKANG)
    gelar = random.choice(GELAR)
    nama = f"{depan} {belakang}".strip()
    if gelar:
        nama = f"{nama}, {gelar}"
    return nama.upper()


def gen_tanggal(start_year=1950, end_year=2023):
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{day:02d}-{month:02d}-{year}"


def gen_rt_rw():
    return f"{random.randint(1,20):03d}/{random.randint(1,20):03d}"


def gen_kode_pos():
    return "".join(random.choices(string.digits, k=5))


def gen_no_k():
    return f"No. K. {random.randint(1000,9999)}.{random.randint(1000000,9999999)}"


def scale_column_widths(widths, target_width):
    scaled = [round(width * target_width / sum(widths)) for width in widths]
    scaled[-1] += target_width - sum(scaled)
    return scaled


def draw_qr_placeholder(draw, box):
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill=(245, 245, 240), outline=TEXT_DARK, width=1)
    cells = random.choice([13, 15])
    cell = max(1, min((x2 - x1 - 6) // cells, (y2 - y1 - 6) // cells))
    ox = x1 + ((x2 - x1) - cells * cell) // 2
    oy = y1 + ((y2 - y1) - cells * cell) // 2
    matrix = [[random.random() < 0.47 for _ in range(cells)] for _ in range(cells)]
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
                px, py = ox + column * cell, oy + row * cell
                draw.rectangle((px, py, px + cell, py + cell), fill=TEXT_DARK)


def gen_family_member(is_kepala=False, idx=1):
    nama = gen_nama()
    nik = gen_nik()
    jk = random.choice(["LAKI-LAKI", "PEREMPUAN"])
    tempat = random.choice(TEMPAT_LAHIR)
    tgl = gen_tanggal()
    agama = random.choice(AGAMA)
    pendidikan = random.choice(PENDIDIKAN)
    pekerjaan = random.choice(PEKERJAAN)
    gol_darah = random.choice(["A", "B", "AB", "O", "-"])

    if is_kepala:
        status_kawin = "KAWIN"
        status_hub = "KEPALA KELUARGA"
    else:
        status_hub = random.choice(["ISTERI", "ANAK", "ANAK", "MENANTU", "CUCU", "ORANGTUA"])
        status_kawin = "KAWIN" if status_hub == "ISTERI" else random.choice(STATUS_KAWIN)
    tgl_perkawinan = (
        gen_tanggal(1970, 2024) if status_kawin == "KAWIN" else "-"
    )

    kewarganegaraan = random.choice(KEWARGANEGARAAN)
    no_paspor = "-" if random.random() > 0.05 else "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    no_kitas = "-" if random.random() > 0.03 else "".join(random.choices(string.digits, k=10))
    ayah = gen_nama() if random.random() > 0.05 else "-"
    ibu = gen_nama() if random.random() > 0.05 else "-"

    return {
        "no": idx,
        "nama": nama,
        "nik": nik,
        "jk": jk,
        "tempat_lahir": tempat,
        "tgl_lahir": tgl,
        "agama": agama,
        "pendidikan": pendidikan,
        "pekerjaan": pekerjaan,
        "gol_darah": gol_darah,
        "status_kawin": status_kawin,
        "tgl_perkawinan": tgl_perkawinan,
        "status_hub": status_hub,
        "kewarganegaraan": kewarganegaraan,
        "no_paspor": no_paspor,
        "no_kitas": no_kitas,
        "ayah": ayah,
        "ibu": ibu,
    }


def gen_kk_data(n_members=None):
    """Generate seluruh data dummy satu KK. n_members: jumlah anggota
    terisi (1-7), sisanya baris kosong hingga 10 baris tabel."""
    if n_members is None:
        n_members = random.randint(1, 7)
    n_members = max(1, min(7, n_members))

    kepala = gen_family_member(is_kepala=True, idx=1)
    members = [kepala]
    for i in range(2, n_members + 1):
        members.append(gen_family_member(is_kepala=False, idx=i))

    desa = random.choice(DESA_POOL)
    kecamatan = random.choice(KECAMATAN_POOL)
    kabupaten = random.choice(KABUPATEN_POOL)
    provinsi = random.choice(PROVINSI_POOL)

    data = {
        "no_k": gen_no_k(),
        "no_kk": gen_no_kk(),
        "nama_kepala": kepala["nama"],
        "alamat": f"{random.choice(['JL.', 'DUSUN', 'KP.'])} {random.choice(NAMA_BELAKANG) or 'MERDEKA'} {random.randint(1,99)}",
        "rt_rw": gen_rt_rw(),
        "desa": desa,
        "kecamatan": kecamatan,
        "kabupaten": kabupaten,
        "kode_pos": gen_kode_pos(),
        "provinsi": provinsi,
        "tgl_dikeluarkan": gen_tanggal(2015, 2024),
        "kepala_ttd": kepala["nama"],
        "pejabat_nama": gen_nama(),
        "pejabat_nip": "".join(random.choices(string.digits, k=18)),
        "use_qr": random.random() < 0.65,
        "members": members,
        "n_members": n_members,
    }
    return data


# =====================================================================
# RENDERER DOKUMEN KK
# =====================================================================
BG_BLUE = (214, 234, 248)       # background kertas KK biru muda
HEADER_BLUE = (41, 98, 158)     # header biru tua dukcapil
LINE_BLUE = (90, 140, 190)
TEXT_DARK = (20, 30, 60)
TEXT_BLUE = (30, 60, 110)


def draw_watermark(draw, w, h):
    """Watermark ornamen halus (garis diagonal + lingkaran samar) sebagai
    pengganti pola batik kompleks - cukup untuk menambah tekstur realistis
    tanpa perlu asset image eksternal."""
    wm_color = (190, 214, 235)
    for i in range(-h, w, 40):
        draw.line([(i, 0), (i + h, h)], fill=wm_color, width=1)
    cx, cy = w // 2, h // 2
    for r in range(60, min(w, h) // 2, 70):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=wm_color, width=1)


def draw_garuda_placeholder(img, x, y, size):
    """Placeholder logo garuda sederhana: perisai + lingkaran, cukup sebagai
    representasi visual tanpa mengklaim akurasi heraldik."""
    draw = ImageDraw.Draw(img)
    gold = (180, 150, 40)
    draw.ellipse([x, y, x + size, y + size * 0.9], outline=gold, width=3)
    draw.polygon([
        (x + size * 0.5, y + size * 0.05),
        (x + size * 0.85, y + size * 0.35),
        (x + size * 0.7, y + size * 0.85),
        (x + size * 0.3, y + size * 0.85),
        (x + size * 0.15, y + size * 0.35),
    ], outline=gold, width=2)


def render_kk_document(data):
    """Render dokumen KK penuh ke PIL Image (KK_W x KK_H) dan kembalikan
    (image, list_of_bboxes) di mana tiap bbox = (class_id, x1,y1,x2,y2)
    dalam koordinat gambar dokumen (sebelum ditempatkan di canvas augmented).
    """
    img = Image.new("RGB", (KK_W, KK_H), BG_BLUE)
    draw = ImageDraw.Draw(img)
    draw_watermark(draw, KK_W, KK_H)

    bboxes = []  # (class_id, x1, y1, x2, y2)

    def add_sensitive_bbox(position, text, font, anchor="lm", padding=2):
        x1, y1, x2, y2 = draw.textbbox(
            position, text, font=font, anchor=anchor
        )
        bboxes.append(
            (
                CLASS_NIK_TEKS,
                x1 - padding,
                y1 - padding,
                x2 + padding,
                y2 + padding,
            )
        )

    f_title = get_font(30, bold=True)
    f_sub = get_font(16, bold=True)
    f_label = get_font(12, bold=False)
    f_val = get_font(12, bold=True)
    f_table_head = get_font(10, bold=True)
    f_table_cell = get_font(10, bold=False)
    f_small = get_font(9, bold=False)

    def fit_table_font(text, max_width, start_size=10):
        for size in range(start_size, 6, -1):
            font = get_font(size)
            x1, _, x2, _ = draw.textbbox((0, 0), text, font=font)
            if x2 - x1 <= max_width:
                return font
        return get_font(7)

    margin = 18
    # border luar dokumen
    draw.rectangle([margin, margin, KK_W - margin, KK_H - margin], outline=HEADER_BLUE, width=2)

    # --- HEADER ---
    draw_garuda_placeholder(img, margin + 15, margin + 8, 70)
    draw.text((KK_W // 2, margin + 15), "KARTU KELUARGA", font=f_title, fill=TEXT_DARK, anchor="mt")
    no_kk_text = f"No. {data['no_kk']}"
    no_kk_xy = (KK_W // 2, margin + 55)
    draw.text(no_kk_xy, no_kk_text, font=f_sub, fill=TEXT_DARK, anchor="mt")
    add_sensitive_bbox(no_kk_xy, no_kk_text, f_sub, anchor="mt")
    no_k_xy = (KK_W - margin - 15, margin + 10)
    draw.text(no_k_xy, data["no_k"], font=f_label, fill=TEXT_DARK, anchor="ra")
    add_sensitive_bbox(no_k_xy, data["no_k"], f_label, anchor="ra")

    y_info = margin + 100
    # kolom kiri info
    left_x = margin + 15
    right_x = KK_W // 2 + 30

    info_left = [
        ("Nama Kepala Keluarga", f": {data['nama_kepala']}", True),
        ("Alamat", f": {data['alamat']}", True),
        ("RT/RW", f": {data['rt_rw']}", True),
        ("Desa/Kelurahan", f": {data['desa']}", True),
    ]
    info_right = [
        ("Kecamatan", f": {data['kecamatan']}", True),
        ("Kabupaten/Kota", f": {data['kabupaten']}", True),
        ("Kode Pos", f": {data['kode_pos']}", True),
        ("Provinsi", f": {data['provinsi']}", True),
    ]

    row_h = 18
    for i, (label, val, sensitive) in enumerate(info_left):
        yy = y_info + i * row_h
        draw.text((left_x, yy), label, font=f_label, fill=TEXT_DARK, anchor="lm")
        vx = left_x + 155
        draw.text((vx, yy), val, font=f_val, fill=TEXT_BLUE, anchor="lm")
        if sensitive:
            add_sensitive_bbox((vx, yy), val, f_val)

    for i, (label, val, sensitive) in enumerate(info_right):
        yy = y_info + i * row_h
        draw.text((right_x, yy), label, font=f_label, fill=TEXT_DARK, anchor="lm")
        vx = right_x + 130
        draw.text((vx, yy), val, font=f_val, fill=TEXT_BLUE, anchor="lm")
        if sensitive:
            add_sensitive_bbox((vx, yy), val, f_val)

    # --- TABEL ANGGOTA KELUARGA (bagian 1) ---
    table1_y = y_info + len(info_left) * row_h + 15
    col1_headers = ["No.", "Nama Lengkap", "NIK", "Jenis\nKelamin",
                     "Tempat Lahir", "Tanggal\nLahir", "Agama", "Pendidikan",
                     "Jenis Pekerjaan", "Gol.\nDarah"]
    table1_x = margin + 10
    table_width = KK_W - 2 * table1_x
    col1_widths = scale_column_widths(
        [32, 175, 150, 75, 110, 85, 75, 150, 145, 60],
        table_width,
    )
    total_w1 = sum(col1_widths)

    header_h = 26
    draw.rectangle([table1_x, table1_y, table1_x + total_w1, table1_y + header_h],
                    fill=(180, 208, 230), outline=LINE_BLUE, width=1)
    cx = table1_x
    for hdr, cw in zip(col1_headers, col1_widths):
        draw.text((cx + cw / 2, table1_y + header_h / 2), hdr, font=f_table_head,
                   fill=TEXT_DARK, anchor="mm", align="center")
        draw.line([(cx, table1_y), (cx, table1_y + header_h)], fill=LINE_BLUE, width=1)
        cx += cw
    draw.line([(cx, table1_y), (cx, table1_y + header_h)], fill=LINE_BLUE, width=1)

    row_h1 = 20
    n_rows = 10
    members = data["members"]
    y = table1_y + header_h
    for r in range(n_rows):
        member = members[r] if r < len(members) else None
        cx = table1_x
        row_vals = []
        if member:
            row_vals = [str(member["no"]), member["nama"], member["nik"], member["jk"],
                        member["tempat_lahir"], member["tgl_lahir"], member["agama"],
                        member["pendidikan"], member["pekerjaan"], member["gol_darah"]]
        else:
            row_vals = [str(r + 1), "", "", "", "", "", "", "", "", ""]

        row_sensitive_cols = set(range(1, len(row_vals)))
        centered_cols = {0, 2, 3, 5, 6, 9}
        cell_x = table1_x
        for ci, (val, cw) in enumerate(zip(row_vals, col1_widths)):
            if val:
                fs = fit_table_font(val, cw - 6)
                anchor = "mm" if ci in centered_cols else "lm"
                position = (
                    (cell_x + cw / 2, y + row_h1 / 2)
                    if anchor == "mm"
                    else (cell_x + 4, y + row_h1 / 2)
                )
                draw.text(position, val, font=fs, fill=TEXT_DARK, anchor=anchor)
                if ci in row_sensitive_cols and member:
                    add_sensitive_bbox(
                        position,
                        val,
                        fs,
                        anchor=anchor,
                        padding=1,
                    )
            draw.line([(cell_x, y), (cell_x, y + row_h1)], fill=LINE_BLUE, width=1)
            cell_x += cw
        draw.line([(cell_x, y), (cell_x, y + row_h1)], fill=LINE_BLUE, width=1)
        draw.line([(table1_x, y), (table1_x + total_w1, y)], fill=LINE_BLUE, width=1)
        y += row_h1
    draw.line([(table1_x, y), (table1_x + total_w1, y)], fill=LINE_BLUE, width=1)
    draw.rectangle([table1_x, table1_y, table1_x + total_w1, y], outline=LINE_BLUE, width=1)

    table1_bottom = y

    # --- TABEL ANGGOTA KELUARGA (bagian 2) ---
    table2_y = table1_bottom + 8
    col2_headers = [
        "No.", "Status\nPernikahan", "Tanggal\nPerkawinan",
        "Status Hubungan\nDalam Keluarga", "Kewarga-\nnegaraan",
        "No. Paspor", "No.\nKITAS/KITAP", "Ayah", "Ibu",
    ]
    table2_x = margin + 10
    col2_widths = scale_column_widths(
        [32, 105, 100, 145, 80, 95, 100, 165, 165],
        KK_W - 2 * table2_x,
    )
    total_w2 = sum(col2_widths)

    header_h2 = 30
    draw.rectangle([table2_x, table2_y, table2_x + total_w2, table2_y + header_h2],
                    fill=(180, 208, 230), outline=LINE_BLUE, width=1)
    cx = table2_x
    for hdr, cw in zip(col2_headers, col2_widths):
        draw.text((cx + cw / 2, table2_y + header_h2 / 2), hdr, font=f_table_head,
                   fill=TEXT_DARK, anchor="mm", align="center")
        draw.line([(cx, table2_y), (cx, table2_y + header_h2)], fill=LINE_BLUE, width=1)
        cx += cw
    draw.line([(cx, table2_y), (cx, table2_y + header_h2)], fill=LINE_BLUE, width=1)

    row_h2 = 20
    y2 = table2_y + header_h2
    for r in range(n_rows):
        member = members[r] if r < len(members) else None
        if member:
            row_vals = [
                str(member["no"]), member["status_kawin"],
                member["tgl_perkawinan"], member["status_hub"],
                member["kewarganegaraan"], member["no_paspor"],
                member["no_kitas"], member["ayah"], member["ibu"],
            ]
        else:
            row_vals = [str(r + 1), "", "", "", "", "", "", "", ""]

        row_sensitive_cols = set(range(1, len(row_vals)))
        centered_cols = set(range(0, 7))
        cell_x = table2_x
        for ci, (val, cw) in enumerate(zip(row_vals, col2_widths)):
            if val:
                fs = fit_table_font(val, cw - 6)
                anchor = "mm" if ci in centered_cols else "lm"
                position = (
                    (cell_x + cw / 2, y2 + row_h2 / 2)
                    if anchor == "mm"
                    else (cell_x + 4, y2 + row_h2 / 2)
                )
                draw.text(position, val, font=fs, fill=TEXT_DARK, anchor=anchor)
                if ci in row_sensitive_cols and member and val != "-":
                    add_sensitive_bbox(
                        position,
                        val,
                        fs,
                        anchor=anchor,
                        padding=1,
                    )
            draw.line([(cell_x, y2), (cell_x, y2 + row_h2)], fill=LINE_BLUE, width=1)
            cell_x += cw
        draw.line([(cell_x, y2), (cell_x, y2 + row_h2)], fill=LINE_BLUE, width=1)
        draw.line([(table2_x, y2), (table2_x + total_w2, y2)], fill=LINE_BLUE, width=1)
        y2 += row_h2
    draw.line([(table2_x, y2), (table2_x + total_w2, y2)], fill=LINE_BLUE, width=1)
    draw.rectangle([table2_x, table2_y, table2_x + total_w2, y2], outline=LINE_BLUE, width=1)

    # --- FOOTER ---
    footer_y = y2 + 15
    draw.text((margin + 15, footer_y), "Dikeluarkan Tanggal", font=f_label, fill=TEXT_DARK, anchor="lm")
    issue_text = f": {data['tgl_dikeluarkan']}"
    issue_xy = (margin + 140, footer_y)
    draw.text(issue_xy, issue_text, font=f_val, fill=TEXT_BLUE, anchor="lm")
    add_sensitive_bbox(issue_xy, issue_text, f_val)
    draw.text((margin + 15, footer_y + 18), "LEMBAR", font=f_label, fill=TEXT_DARK, anchor="lm")
    lembar_txt = ["I.  Kepala Keluarga", "II.  Dukuh", "III. Desa/Kelurahan", "IV. Kecamatan"]
    for i, t in enumerate(lembar_txt):
        draw.text((margin + 140, footer_y + 18 + i * 14), t, font=f_small, fill=TEXT_DARK, anchor="lm")

    sig_x = KK_W // 2 + 20
    draw.text((sig_x, footer_y), "KEPALA KELUARGA", font=f_label, fill=TEXT_DARK, anchor="mm")
    kepala_xy = (sig_x, footer_y + 55)
    draw.text(kepala_xy, data["kepala_ttd"], font=f_val, fill=TEXT_DARK, anchor="mm")
    add_sensitive_bbox(kepala_xy, data["kepala_ttd"], f_val, anchor="mm")
    draw.line([(sig_x - 60, footer_y + 65), (sig_x + 60, footer_y + 65)], fill=TEXT_DARK, width=1)
    draw.text((sig_x, footer_y + 75), "Tanda Tangan/Cap Jempol", font=f_small, fill=TEXT_DARK, anchor="mm")

    sig2_x = KK_W - margin - 130
    nip_text = f"NIP. {data['pejabat_nip']}"
    if data.get("use_qr", True):
        draw.text((sig2_x, footer_y), "DITANDATANGANI SECARA ELEKTRONIK", font=f_small, fill=TEXT_DARK, anchor="mm")
        draw.text((sig2_x, footer_y + 12), "DINAS KEPENDUDUKAN DAN CATATAN SIPIL", font=f_small, fill=TEXT_DARK, anchor="mm")
        pejabat_xy = (sig2_x, footer_y + 28)
        draw.text(pejabat_xy, data["pejabat_nama"], font=f_val, fill=TEXT_DARK, anchor="mm")
        add_sensitive_bbox(pejabat_xy, data["pejabat_nama"], f_val, anchor="mm")

        qr_box = (sig2_x - 38, footer_y + 40, sig2_x + 38, footer_y + 116)
        draw_qr_placeholder(draw, qr_box)
        bboxes.append((CLASS_NIK_TEKS, *qr_box))
        nip_xy = (sig2_x, footer_y + 126)
    else:
        draw.text((sig2_x, footer_y), "KEPALA DINAS KEPENDUDUKAN DAN", font=f_small, fill=TEXT_DARK, anchor="mm")
        draw.text((sig2_x, footer_y + 12), "PENCATATAN SIPIL", font=f_small, fill=TEXT_DARK, anchor="mm")
        stamp_x, stamp_y = sig2_x - 58, footer_y + 55
        draw.ellipse(
            (stamp_x - 34, stamp_y - 34, stamp_x + 34, stamp_y + 34),
            outline=(55, 85, 165),
            width=2,
        )
        draw.ellipse(
            (stamp_x - 27, stamp_y - 27, stamp_x + 27, stamp_y + 27),
            outline=(55, 85, 165),
            width=1,
        )
        for _ in range(5):
            draw.line(
                (
                    random.randint(sig2_x - 10, sig2_x + 12),
                    random.randint(footer_y + 38, footer_y + 60),
                    random.randint(sig2_x + 35, sig2_x + 72),
                    random.randint(footer_y + 55, footer_y + 78),
                ),
                fill=TEXT_DARK,
                width=2,
            )
        pejabat_xy = (sig2_x + 20, footer_y + 88)
        draw.text(pejabat_xy, data["pejabat_nama"], font=f_val, fill=TEXT_DARK, anchor="mm")
        add_sensitive_bbox(pejabat_xy, data["pejabat_nama"], f_val, anchor="mm")
        draw.line(
            (sig2_x - 55, footer_y + 98, sig2_x + 95, footer_y + 98),
            fill=TEXT_DARK,
            width=1,
        )
        nip_xy = (sig2_x + 20, footer_y + 112)

    draw.text(nip_xy, nip_text, font=f_small, fill=TEXT_DARK, anchor="mm")
    add_sensitive_bbox(nip_xy, nip_text, f_small, anchor="mm", padding=1)

    # class-6 bbox mencakup seluruh dokumen (di dalam border)
    kk_bbox = (CLASS_KK, margin, margin, KK_W - margin, KK_H - margin)
    bboxes.insert(0, kk_bbox)

    # clip semua bbox ke dalam dimensi gambar
    clipped = []
    for cid, x1, y1, x2, y2 in bboxes:
        x1, y1, x2, y2 = clip_bbox((x1, y1, x2, y2), KK_W, KK_H)
        if x2 - x1 > 2 and y2 - y1 > 2:
            clipped.append((cid, x1, y1, x2, y2))

    return img, clipped


# =====================================================================
# BACKGROUND KONTEKSTUAL (8 variasi)
# =====================================================================
def make_background(kind, w, h):
    """Generate background kontekstual sebagai numpy array BGR uint8."""
    bg = np.zeros((h, w, 3), dtype=np.uint8)

    if kind == "desk_wood":
        base = np.array([60, 90, 130], dtype=np.float32)  # BGR coklat kayu
        for y in range(h):
            stripe = 10 * math.sin(y * 0.05) + np.random.normal(0, 4)
            bg[y, :] = np.clip(base + stripe, 0, 255)
        noise = np.random.normal(0, 6, (h, w, 3))
        bg = np.clip(bg.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    elif kind == "desk_white":
        base = np.array([235, 235, 232], dtype=np.float32)
        noise = np.random.normal(0, 4, (h, w, 3))
        bg[:] = np.clip(base + noise, 0, 255).astype(np.uint8)

    elif kind == "cloth_dark":
        base = np.array([40, 38, 42], dtype=np.float32)
        noise = np.random.normal(0, 8, (h, w, 3))
        bg[:] = np.clip(base + noise, 0, 255).astype(np.uint8)

    elif kind == "cloth_light":
        base = np.array([200, 198, 195], dtype=np.float32)
        noise = np.random.normal(0, 7, (h, w, 3))
        bg[:] = np.clip(base + noise, 0, 255).astype(np.uint8)

    elif kind == "hand_skin":
        base = np.array([120, 155, 205], dtype=np.float32)  # BGR kulit
        for y in range(h):
            grad = (y / h) * 20
            bg[y, :] = np.clip(base + grad, 0, 255)
        noise = np.random.normal(0, 5, (h, w, 3))
        bg = np.clip(bg.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    elif kind == "concrete":
        base = np.array([150, 148, 145], dtype=np.float32)
        noise = np.random.normal(0, 12, (h, w, 3))
        bg[:] = np.clip(base + noise, 0, 255).astype(np.uint8)
        bg = cv2.GaussianBlur(bg, (3, 3), 0)

    elif kind == "gradient":
        c1 = np.array([np.random.randint(30, 90) for _ in range(3)], dtype=np.float32)
        c2 = np.array([np.random.randint(120, 220) for _ in range(3)], dtype=np.float32)
        for y in range(h):
            t = y / max(1, h - 1)
            bg[y, :] = np.clip(c1 * (1 - t) + c2 * t, 0, 255)

    elif kind == "noise_paper":
        base = np.array([225, 225, 220], dtype=np.float32)
        noise = np.random.normal(0, 10, (h, w, 3))
        bg[:] = np.clip(base + noise, 0, 255).astype(np.uint8)

    else:
        bg[:] = (200, 200, 200)

    return bg


def paper_border_value():
    """Random border color untuk warpAffine dokumen kertas (KK, Resi):
    sedikit off-white agar tepi terlihat natural, bukan pure white."""
    b = random.randint(240, 255)
    g = random.randint(240, 255)
    r = random.randint(235, 250)
    return (b, g, r)


# =====================================================================
# CANVAS PLACEMENT - dengan fallback fit jika dokumen > canvas
# =====================================================================
def scale_and_place_on_canvas(doc_bgr, canvas_w, canvas_h, target_scale=0.7,
                                jitter=True):
    """Scale dokumen (doc_bgr, numpy array) agar muat proporsional di dalam
    canvas_w x canvas_h, dengan fallback fit (shrink-to-fit) apabila dokumen
    lebih besar dari canvas pada skala target. Return offset (ox, oy) dan
    scale factor yang dipakai, TIDAK menempel ke canvas di sini (canvas
    dipilih terpisah - lihat generate_sample).
    """
    doc_h, doc_w = doc_bgr.shape[:2]

    scale = target_scale * min(canvas_w / doc_w, canvas_h / doc_h)
    new_w, new_h = int(doc_w * scale), int(doc_h * scale)

    # fallback fit: jika masih > canvas (target_scale terlalu besar / doc aneh)
    if new_w > canvas_w or new_h > canvas_h:
        fit_scale = min(canvas_w / doc_w, canvas_h / doc_h) * 0.95
        scale = fit_scale
        new_w, new_h = int(doc_w * scale), int(doc_h * scale)

    new_w = max(1, new_w)
    new_h = max(1, new_h)
    resized = cv2.resize(doc_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    max_ox = max(0, canvas_w - new_w)
    max_oy = max(0, canvas_h - new_h)
    if jitter and max_ox > 0:
        ox = random.randint(0, max_ox)
    else:
        ox = max_ox // 2
    if jitter and max_oy > 0:
        oy = random.randint(0, max_oy)
    else:
        oy = max_oy // 2

    return resized, ox, oy, scale


def pick_canvas_size(scenario):
    """Canvas dipilih SETELAH rotasi tahu skala dokumen agar tidak pernah
    menghasilkan gambar kosong. Untuk kesederhanaan & konsistensi, canvas
    base size mengikuti proporsi KK (A4 landscape) dengan variasi ukuran
    per skenario (far_away -> canvas lebih besar relatif thd dokumen,
    close_up -> canvas lebih kecil / lebih rapat)."""
    base_w, base_h = 1400, 1000
    if scenario == "far_away":
        return int(base_w * 1.3), int(base_h * 1.3)
    if scenario == "close_up":
        return int(base_w * 0.75), int(base_h * 0.75)
    if scenario in ("stacked_docs", "scattered_cards", "complex_bg"):
        return int(base_w * 1.15), int(base_h * 1.15)
    return base_w, base_h


# =====================================================================
# FINGER OCCLUSION REALISTIS
# =====================================================================
def draw_finger(canvas, x, y, length, width, angle_deg, skin_tone=None):
    """Gambar jari realistis: gradien kulit, garis lipatan ruas, dan kuku
    di ujung bebas. canvas: numpy BGR array (dimodifikasi in-place).
    x,y: pangkal jari (biasanya di tepi canvas). angle_deg: arah menuju
    dalam frame (0 = ke kanan)."""
    h, w = canvas.shape[:2]
    if skin_tone is None:
        skin_tone = (
            random.randint(110, 150),
            random.randint(150, 185),
            random.randint(195, 230),
        )  # BGR

    overlay = canvas.copy()
    angle_rad = math.radians(angle_deg)
    dx, dy = math.cos(angle_rad), math.sin(angle_rad)
    tip_x = x + dx * length
    tip_y = y + dy * length

    # badan jari sebagai poligon meruncing sedikit + gradien
    n_seg = 12
    perp_x, perp_y = -dy, dx
    poly_top, poly_bot = [], []
    for i in range(n_seg + 1):
        t = i / n_seg
        cx = x + dx * length * t
        cy = y + dy * length * t
        seg_width = width * (1.0 - 0.15 * t)  # sedikit meruncing
        poly_top.append((cx + perp_x * seg_width / 2, cy + perp_y * seg_width / 2))
        poly_bot.append((cx - perp_x * seg_width / 2, cy - perp_y * seg_width / 2))
    poly = poly_top + poly_bot[::-1]
    poly = np.array(poly, dtype=np.int32)

    # gradien kulit: base -> sedikit lebih terang di ujung (highlight sederhana)
    base_color = np.array(skin_tone, dtype=np.float32)
    light_color = np.clip(base_color + 25, 0, 255)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [poly], 255)

    grad_layer = overlay.copy().astype(np.float32)
    ys, xs = np.where(mask > 0)
    if len(xs) > 0:
        proj = ((xs - x) * dx + (ys - y) * dy) / max(1.0, length)
        proj = np.clip(proj, 0, 1)
        for ch in range(3):
            grad_layer[ys, xs, ch] = base_color[ch] * (1 - proj) + light_color[ch] * proj
    overlay = np.where(mask[..., None] > 0, grad_layer.astype(np.uint8), overlay)

    # lipatan ruas (2 garis melintang di 35% dan 68% panjang jari)
    for frac in (0.35, 0.68):
        jx = x + dx * length * frac
        jy = y + dy * length * frac
        seg_width = width * (1.0 - 0.15 * frac)
        p1 = (int(jx + perp_x * seg_width / 2), int(jy + perp_y * seg_width / 2))
        p2 = (int(jx - perp_x * seg_width / 2), int(jy - perp_y * seg_width / 2))
        fold_color = tuple(int(c * 0.85) for c in skin_tone)
        cv2.line(overlay, p1, p2, fold_color, 1, cv2.LINE_AA)

    # kuku di ujung bebas (jika ujung jauh dari tepi canvas, artinya "bebas")
    nail_w = width * 0.55
    nail_len = length * 0.14
    nail_base_x = x + dx * length * 0.86
    nail_base_y = y + dy * length * 0.86
    nail_color = (
        min(255, skin_tone[0] + 35), min(255, skin_tone[1] + 30), min(255, skin_tone[2] + 25)
    )
    nail_poly = np.array([
        (nail_base_x + perp_x * nail_w / 2, nail_base_y + perp_y * nail_w / 2),
        (tip_x + perp_x * nail_w / 2.4, tip_y + perp_y * nail_w / 2.4),
        (tip_x - perp_x * nail_w / 2.4, tip_y - perp_y * nail_w / 2.4),
        (nail_base_x - perp_x * nail_w / 2, nail_base_y - perp_y * nail_w / 2),
    ], dtype=np.int32)
    cv2.fillPoly(overlay, [nail_poly], nail_color)
    cv2.polylines(overlay, [nail_poly], True, tuple(int(c * 0.8) for c in nail_color), 1, cv2.LINE_AA)

    canvas[:] = overlay
    x1 = int(min(x, tip_x, *[p[0] for p in poly]))
    y1 = int(min(y, tip_y, *[p[1] for p in poly]))
    x2 = int(max(x, tip_x, *[p[0] for p in poly]))
    y2 = int(max(y, tip_y, *[p[1] for p in poly]))
    return clip_bbox((x1, y1, x2, y2), w, h)


def apply_finger_occlusion(canvas, n_fingers=None):
    """Terapkan 1-3 jari dari tepi canvas, kembalikan list bbox occluder
    (dalam koordinat canvas) untuk dipakai visibility check."""
    h, w = canvas.shape[:2]
    if n_fingers is None:
        n_fingers = random.randint(1, 3)
    occluder_rects = []
    edges = ["bottom", "left", "right", "top"]
    chosen_edges = random.sample(edges, min(n_fingers, len(edges)))
    for edge in chosen_edges:
        length = random.randint(int(h * 0.25), int(h * 0.45))
        width = random.randint(int(w * 0.06), int(w * 0.1))
        if edge == "bottom":
            x = random.randint(int(w * 0.2), int(w * 0.8))
            y = h - 5
            angle = random.uniform(-100, -80)
        elif edge == "top":
            x = random.randint(int(w * 0.2), int(w * 0.8))
            y = 5
            angle = random.uniform(80, 100)
        elif edge == "left":
            x = 5
            y = random.randint(int(h * 0.2), int(h * 0.8))
            angle = random.uniform(-15, 15)
        else:  # right
            x = w - 5
            y = random.randint(int(h * 0.2), int(h * 0.8))
            angle = random.uniform(165, 195)
        rect = draw_finger(canvas, x, y, length, width, angle)
        occluder_rects.append(rect)
    return occluder_rects


# =====================================================================
# EFEK KHUSUS DOKUMEN KERTAS: paper_crumple, scan_artifact
# =====================================================================
def apply_paper_crumple(doc_bgr):
    """Simulasikan kertas kusut/terlipat: distorsi mesh ringan + garis
    lipatan gelap + shading acak. Bbox tidak perlu diproyeksikan ulang
    lewat matrix karena distorsi ini bersifat lokal non-affine kecil;
    dilakukan SEBELUM transform global (rotasi/scale) sehingga bbox
    global tetap valid, hanya tekstur yang berubah."""
    h, w = doc_bgr.shape[:2]
    out = doc_bgr.copy().astype(np.float32)

    n_folds = random.randint(2, 4)
    for _ in range(n_folds):
        if random.random() < 0.5:
            # lipatan horizontal
            fy = random.randint(int(h * 0.15), int(h * 0.85))
            band = random.randint(3, 8)
            darken = random.uniform(0.75, 0.9)
            y0, y1 = max(0, fy - band), min(h, fy + band)
            out[y0:y1, :, :] *= darken
        else:
            fx = random.randint(int(w * 0.15), int(w * 0.85))
            band = random.randint(3, 8)
            darken = random.uniform(0.75, 0.9)
            x0, x1 = max(0, fx - band), min(w, fx + band)
            out[:, x0:x1, :] *= darken

    # shading gradient ringan mensimulasikan permukaan tidak rata
    grad = np.zeros((h, w), dtype=np.float32)
    for _ in range(3):
        cx, cy = random.randint(0, w), random.randint(0, h)
        r = random.randint(int(w * 0.2), int(w * 0.5))
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        grad += np.clip(1.0 - d / r, 0, 1) * random.uniform(-15, 10)
    out += grad[..., None]

    out = np.clip(out, 0, 255).astype(np.uint8)
    return out


def apply_scan_artifact(doc_bgr):
    """Simulasikan hasil scan: garis-garis scanner halus (banding) +
    tint kekuningan ringan + sedikit penurunan kontras."""
    h, w = doc_bgr.shape[:2]
    out = doc_bgr.copy().astype(np.float32)

    # tint kekuningan (kurangi channel B sedikit, tambah R/G sedikit - BGR order)
    out[..., 0] *= random.uniform(0.90, 0.97)   # B turun
    out[..., 1] *= random.uniform(0.98, 1.03)   # G
    out[..., 2] *= random.uniform(1.02, 1.08)   # R naik -> kekuningan

    # garis scanner horizontal periodik + noise banding
    n_lines = random.randint(2, 6)
    for _ in range(n_lines):
        ly = random.randint(0, h - 1)
        thickness = random.choice([1, 1, 2])
        intensity = random.uniform(0.85, 0.96)
        y0, y1 = max(0, ly - thickness // 2), min(h, ly + thickness // 2 + 1)
        out[y0:y1, :, :] *= intensity

    out = np.clip(out, 0, 255).astype(np.uint8)
    # sedikit turunkan kontras (khas scan lama)
    out = cv2.convertScaleAbs(out, alpha=0.95, beta=8)
    return out


# =====================================================================
# TRANSFORM HELPERS (rotasi, perspektif, motion blur)
# =====================================================================
def build_rotation_matrix(angle_deg, center, scale=1.0):
    return cv2.getRotationMatrix2D(center, angle_deg, scale)


def apply_affine_full(doc_bgr, angle_deg, canvas_w, canvas_h, border_value,
                       place_scale=0.7, jitter=True):
    """Pipeline transform standar: scale+place lalu rotate dalam frame
    canvas penuh. Mengembalikan (result_bgr, M_full, doc_rect_before_rotate)
    di mana M_full adalah matriks affine 2x3 dari koordinat DOKUMEN ASLI
    (sebelum resize) ke koordinat CANVAS AKHIR - dipakai project_bbox_to_canvas.
    """
    doc_h, doc_w = doc_bgr.shape[:2]

    resized, ox, oy, scale = scale_and_place_on_canvas(
        doc_bgr, canvas_w, canvas_h, target_scale=place_scale, jitter=jitter)
    new_h, new_w = resized.shape[:2]

    # tempatkan resized doc di atas canvas kosong (border_value) dahulu
    placed = np.full((canvas_h, canvas_w, 3), border_value, dtype=np.uint8)
    placed[oy:oy + new_h, ox:ox + new_w] = resized

    # rotasi di sekitar pusat dokumen yang sudah ditempatkan
    center = (ox + new_w / 2.0, oy + new_h / 2.0)
    M_rot = build_rotation_matrix(angle_deg, center, scale=1.0)
    rotated = cv2.warpAffine(placed, M_rot, (canvas_w, canvas_h),
                              borderValue=border_value, flags=cv2.INTER_LINEAR)

    # matriks total: (x,y) doc asli -> scale -> translate(ox,oy) -> rotate
    M_scale_translate = np.array([
        [scale, 0, ox],
        [0, scale, oy],
    ], dtype=np.float64)

    # gabungkan M_rot (2x3, sudah termasuk translasi) dengan M_scale_translate
    # perkalian matriks affine: hasil = M_rot ∘ M_scale_translate
    A_rot = M_rot[:, :2]
    t_rot = M_rot[:, 2]
    A_st = M_scale_translate[:, :2]
    t_st = M_scale_translate[:, 2]

    A_full = A_rot @ A_st
    t_full = A_rot @ t_st + t_rot
    M_full = np.hstack([A_full, t_full.reshape(2, 1)])

    return rotated, M_full


def apply_perspective_warp(canvas_bgr, strength=0.12):
    """Distorsi perspektif ringan pada seluruh canvas. Return (result, M3x3)
    matriks perspektif untuk proyeksi bbox (dipakai via perspectiveTransform,
    bukan project_bbox_to_canvas affine)."""
    h, w = canvas_bgr.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    jx, jy = w * strength, h * strength
    dst = np.float32([
        [random.uniform(0, jx), random.uniform(0, jy)],
        [w - random.uniform(0, jx), random.uniform(0, jy)],
        [w - random.uniform(0, jx), h - random.uniform(0, jy)],
        [random.uniform(0, jx), h - random.uniform(0, jy)],
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    border_value = paper_border_value()
    result = cv2.warpPerspective(canvas_bgr, M, (w, h), borderValue=border_value)
    return result, M


def project_bbox_perspective(bbox_xyxy, M3x3):
    x1, y1, x2, y2 = bbox_xyxy
    pts = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(pts, M3x3).reshape(-1, 2)
    xs, ys = transformed[:, 0], transformed[:, 1]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def apply_motion_blur(img_bgr, size=None, angle_deg=None):
    if size is None:
        size = random.choice([7, 9, 11, 13])
    if angle_deg is None:
        angle_deg = random.uniform(0, 180)
    kernel = np.zeros((size, size), dtype=np.float32)
    kernel[size // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, M, (size, size))
    kernel /= max(kernel.sum(), 1e-6)
    return cv2.filter2D(img_bgr, -1, kernel)


def apply_glare(img_bgr, strength=0.5):
    h, w = img_bgr.shape[:2]
    cx, cy = random.randint(0, w), random.randint(0, h)
    r = random.randint(int(min(w, h) * 0.15), int(min(w, h) * 0.4))
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    glare_mask = np.clip(1.0 - d / r, 0, 1) ** 2 * strength * 255
    out = img_bgr.astype(np.float32)
    out += glare_mask[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_shadow(img_bgr, strength=0.5):
    h, w = img_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.float32)
    # bayangan sebagai poligon acak di salah satu sisi
    side = random.choice(["left", "right", "top", "bottom"])
    pts = []
    if side == "left":
        wshadow = int(w * random.uniform(0.25, 0.5))
        pts = [(0, 0), (wshadow, 0), (int(wshadow * 0.6), h), (0, h)]
    elif side == "right":
        wshadow = int(w * random.uniform(0.25, 0.5))
        pts = [(w, 0), (w - wshadow, 0), (w - int(wshadow * 0.6), h), (w, h)]
    elif side == "top":
        hshadow = int(h * random.uniform(0.25, 0.5))
        pts = [(0, 0), (w, 0), (w, hshadow), (0, int(hshadow * 0.6))]
    else:
        hshadow = int(h * random.uniform(0.25, 0.5))
        pts = [(0, h), (w, h), (w, h - hshadow), (0, h - int(hshadow * 0.6))]
    cv2.fillPoly(mask, [np.array(pts, dtype=np.int32)], 1.0)
    mask = cv2.GaussianBlur(mask, (31, 31), 0)
    out = img_bgr.astype(np.float32)
    darken = 1.0 - mask[..., None] * strength
    out *= darken
    return np.clip(out, 0, 255).astype(np.uint8)


# =====================================================================
# POST-PROCESSING
# =====================================================================
def apply_postprocessing(img_bgr, scenario):
    out = img_bgr.copy()

    if scenario == "dark_lighting":
        out = cv2.convertScaleAbs(out, alpha=random.uniform(0.45, 0.65), beta=random.randint(-20, 0))
    elif scenario == "bright_overexp":
        out = cv2.convertScaleAbs(out, alpha=random.uniform(1.25, 1.6), beta=random.randint(20, 45))
    else:
        alpha = random.uniform(0.92, 1.08)
        beta = random.randint(-8, 8)
        out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)

    if random.random() < 0.5:
        noise = np.random.normal(0, random.uniform(2, 8), out.shape).astype(np.float32)
        out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    if random.random() < 0.3:
        k = random.choice([3, 5])
        out = cv2.GaussianBlur(out, (k, k), 0)

    if random.random() < 0.6:
        quality = random.randint(45, 85)
        ok, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            out = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    return out


# =====================================================================
# GENERATE SAMPLE - orkestrasi utama per skenario
# =====================================================================
def generate_sample(scenario=None, use_qr=None):
    """Generate satu sample (image_bgr, list_of_yolo_labels).
    list_of_yolo_labels: list of (class_id, cx, cy, w, h) ternormalisasi.
    """
    if scenario is None:
        scenario = random.choice(SCENARIOS)

    data = gen_kk_data()
    if use_qr is not None:
        data["use_qr"] = use_qr
    doc_img, doc_bboxes = render_kk_document(data)  # doc_bboxes: (cid,x1,y1,x2,y2) di koord dokumen asli
    doc_bgr = cv2.cvtColor(np.array(doc_img), cv2.COLOR_RGB2BGR)
    doc_h, doc_w = doc_bgr.shape[:2]

    canvas_w, canvas_h = pick_canvas_size(scenario)
    border_value = paper_border_value()

    # pra-proses dokumen (efek lokal, sebelum transform global) --------
    if scenario == "paper_crumple":
        doc_bgr = apply_paper_crumple(doc_bgr)
    if scenario == "damaged_card":
        # goresan/lipatan lebih agresif sebagai "damage"
        doc_bgr = apply_paper_crumple(doc_bgr)
        n_scratch = random.randint(2, 5)
        for _ in range(n_scratch):
            p1 = (random.randint(0, doc_w), random.randint(0, doc_h))
            p2 = (random.randint(0, doc_w), random.randint(0, doc_h))
            cv2.line(doc_bgr, p1, p2, (200, 200, 200), random.randint(1, 3), cv2.LINE_AA)

    # tentukan sudut rotasi sesuai skenario ------------------------------
    angle = 0.0
    place_scale = 0.7
    if scenario == "tilt_mild":
        angle = random.uniform(-8, 8)
    elif scenario == "tilt_strong":
        angle = random.uniform(-25, 25)
    elif scenario == "rotation_free":
        angle = random.uniform(-180, 180)
    elif scenario == "far_away":
        place_scale = random.uniform(0.35, 0.5)
    elif scenario == "close_up":
        place_scale = random.uniform(0.85, 0.98)
        angle = random.uniform(-5, 5)
    else:
        angle = random.uniform(-4, 4)
        place_scale = random.uniform(0.6, 0.78)

    # background dasar (canvas dipilih SETELAH kita tahu ukuran akhir) --
    bg_kind = random.choice(BACKGROUNDS)
    if scenario == "face_background":
        bg_kind = random.choice(["hand_skin", "cloth_light", "cloth_dark"])
    elif scenario == "complex_bg":
        bg_kind = random.choice(["desk_wood", "concrete", "noise_paper"])
    canvas_bg = make_background(bg_kind, canvas_w, canvas_h)

    # transform affine penuh (scale+place+rotate) -----------------------
    result, M_full = apply_affine_full(
        doc_bgr, angle, canvas_w, canvas_h, border_value,
        place_scale=place_scale, jitter=True,
    )

    # composite: gunakan mask non-border sebagai area dokumen di atas background
    diff = np.any(np.abs(result.astype(np.int16) - np.array(border_value, dtype=np.int16)) > 6, axis=2)
    mask = diff.astype(np.uint8) * 255
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    mask_f = (mask.astype(np.float32) / 255.0)[..., None]
    canvas = (result.astype(np.float32) * mask_f + canvas_bg.astype(np.float32) * (1 - mask_f)).astype(np.uint8)

    # proyeksikan semua bbox dokumen ke koordinat canvas -----------------
    projected = []
    for cid, x1, y1, x2, y2 in doc_bboxes:
        px1, py1, px2, py2 = project_bbox_to_canvas((x1, y1, x2, y2), M_full)
        projected.append((cid, px1, py1, px2, py2))

    # === CLOSURE FIX: project_extra pakai default argument utk freeze
    # nilai per-iterasi loop (mis. saat menambahkan dokumen tumpukan
    # tambahan dgn transform berbeda per iterasi) ===
    extra_projected_batches = []  # list of list-of-bbox, satu per extra doc

    def project_extra(bboxes_src, M=M_full):
        """M di-default agar ter-freeze pada nilai M saat fungsi ini
        dibuat/dipanggil dalam loop, bukan merujuk ke variabel M_full
        yang mungkin sudah berubah di iterasi berikutnya."""
        out = []
        for cid, x1, y1, x2, y2 in bboxes_src:
            px1, py1, px2, py2 = project_bbox_to_canvas((x1, y1, x2, y2), M)
            out.append((cid, px1, py1, px2, py2))
        return out

    # --- skenario khusus: stacked_docs (tumpukan dokumen kertas) -------
    if scenario == "stacked_docs":
        n_extra = random.randint(1, 3)
        extra_main_rects = []  # bbox class-6 dari tiap extra doc (utk occluder & visibility)
        # offset arah tumpuk (mis. "kartu di bawah sedikit tergeser") agar
        # extra doc tidak pernah tertutup TOTAL oleh main doc - meniru cara
        # orang menumpuk kertas fisik (selalu ada tepi yg terlihat)
        stack_dx = int(canvas_w * random.uniform(0.06, 0.14)) * random.choice([-1, 1])
        stack_dy = int(canvas_h * random.uniform(0.05, 0.12)) * random.choice([-1, 1])

        for i in range(n_extra):
            extra_data = gen_kk_data()
            extra_doc_img, extra_doc_bboxes = render_kk_document(extra_data)
            extra_doc_bgr = cv2.cvtColor(np.array(extra_doc_img), cv2.COLOR_RGB2BGR)

            extra_angle = random.uniform(-15, 15)
            extra_scale = place_scale * random.uniform(0.85, 1.0)
            extra_border = paper_border_value()
            extra_result, M_extra_i = apply_affine_full(
                extra_doc_bgr, extra_angle, canvas_w, canvas_h, extra_border,
                place_scale=extra_scale, jitter=True,
            )
            # geser extra doc (dan matrix-nya) sesuai offset tumpuk bertingkat
            # supaya setiap layer terlihat sedikit "mencuat" dari tumpukan
            layer_dx = stack_dx * (i + 1)
            layer_dy = stack_dy * (i + 1)
            T_layer = np.float32([[1, 0, layer_dx], [0, 1, layer_dy]])
            extra_result = cv2.warpAffine(
                extra_result, T_layer, (canvas_w, canvas_h), borderValue=extra_border)
            M_extra_i = np.array([
                [M_extra_i[0, 0], M_extra_i[0, 1], M_extra_i[0, 2] + layer_dx],
                [M_extra_i[1, 0], M_extra_i[1, 1], M_extra_i[1, 2] + layer_dy],
            ], dtype=np.float64)
            # composite extra doc SEBELUM main doc jika ditumpuk di bawah,
            # atau setelah jika di atas - sederhana: tumpuk berurutan, extra
            # doc ke-i digambar sebelum canvas utama utk efek "di bawah"
            ediff = np.any(np.abs(extra_result.astype(np.int16) - np.array(extra_border, dtype=np.int16)) > 6, axis=2)
            emask = (ediff.astype(np.uint8) * 255)
            emask = cv2.GaussianBlur(emask, (3, 3), 0)
            emask_f = (emask.astype(np.float32) / 255.0)[..., None]
            canvas = (extra_result.astype(np.float32) * emask_f + canvas.astype(np.float32) * (1 - emask_f)).astype(np.uint8)

            extra_proj = project_extra(extra_doc_bboxes, M=M_extra_i)
            extra_projected_batches.append(extra_proj)
            main_class_bbox = next((b for b in extra_proj if b[0] == CLASS_KK), None)
            if main_class_bbox:
                extra_main_rects.append(main_class_bbox[1:])

        # composite dokumen UTAMA di atas semua extra (paling atas = paling depan)
        canvas = (result.astype(np.float32) * mask_f + canvas.astype(np.float32) * (1 - mask_f)).astype(np.uint8)

        # visibility check: kartu utama dicek terhadap SEMUA extra rects
        all_extra_rects = extra_main_rects
        main_kk_bbox = next((b for b in projected if b[0] == CLASS_KK), None)
        if main_kk_bbox and all_extra_rects:
            vis_ratio = compute_visible_ratio(main_kk_bbox[1:], all_extra_rects)
            if vis_ratio < MIN_VISIBLE:
                # dorong dokumen utama sedikit agar lebih terlihat (retry sederhana)
                pass  # diserahkan ke filtering akhir di bawah

        # untuk tiap extra doc idx, occluder HANYA extra_cards[idx+1:] (dan
        # main doc di atas semuanya) - karena main doc selalu paling depan,
        # occluder efektif utk extra[i] adalah extra[i+1:] + main doc
        final_extra_labels = []
        for idx, extra_proj in enumerate(extra_projected_batches):
            occluders = []
            for later in extra_projected_batches[idx + 1:]:
                later_main = next((b for b in later if b[0] == CLASS_KK), None)
                if later_main:
                    occluders.append(later_main[1:])
            if main_kk_bbox:
                occluders.append(main_kk_bbox[1:])
            extra_main = next((b for b in extra_proj if b[0] == CLASS_KK), None)
            if extra_main:
                vis = compute_visible_ratio(extra_main[1:], occluders)
                if vis >= MIN_VISIBLE:
                    # sertakan hanya class-6 utk extra (nik_teks extra doc
                    # terlalu kecil/occluded utk dipertahankan secara wajar)
                    final_extra_labels.append(extra_main)
                    # nik_teks milik extra doc ini yang overlap rendah dgn occluder juga disertakan jika cukup visible
                    for cid, x1, y1, x2, y2 in extra_proj:
                        if cid == CLASS_NIK_TEKS:
                            v2 = compute_visible_ratio((x1, y1, x2, y2), occluders)
                            if v2 >= MIN_VISIBLE:
                                final_extra_labels.append((cid, x1, y1, x2, y2))
        projected.extend(final_extra_labels)

    # --- skenario khusus: scattered_cards (dokumen tersebar, tidak overlap
    # signifikan, hanya distractor visual) -------------------------------
    if scenario == "scattered_cards":
        n_extra = random.randint(1, 2)
        for _ in range(n_extra):
            extra_data = gen_kk_data()
            extra_doc_img, _ = render_kk_document(extra_data)
            extra_doc_bgr = cv2.cvtColor(np.array(extra_doc_img), cv2.COLOR_RGB2BGR)
            small_scale = place_scale * random.uniform(0.3, 0.45)
            extra_angle = random.uniform(-40, 40)
            extra_border = paper_border_value()
            # tempatkan di pojok yang tidak overlap area dokumen utama secara signifikan
            resized, ox, oy, _ = scale_and_place_on_canvas(
                extra_doc_bgr, canvas_w, canvas_h, target_scale=small_scale, jitter=True)
            eh, ew = resized.shape[:2]
            temp = np.full((canvas_h, canvas_w, 3), extra_border, dtype=np.uint8)
            temp[oy:oy + eh, ox:ox + ew] = resized
            M_rot = build_rotation_matrix(extra_angle, (ox + ew / 2, oy + eh / 2))
            rotated = cv2.warpAffine(temp, M_rot, (canvas_w, canvas_h), borderValue=extra_border)
            ediff = np.any(np.abs(rotated.astype(np.int16) - np.array(extra_border, dtype=np.int16)) > 6, axis=2)
            emask = cv2.GaussianBlur((ediff.astype(np.uint8) * 255), (3, 3), 0)
            emask_f = (emask.astype(np.float32) / 255.0)[..., None]
            canvas = (rotated.astype(np.float32) * emask_f + canvas.astype(np.float32) * (1 - emask_f)).astype(np.uint8)

    # --- skenario khusus: finger_occlusion ------------------------------
    if scenario == "finger_occlusion":
        occluder_rects = apply_finger_occlusion(canvas)
        filtered = []
        for cid, x1, y1, x2, y2 in projected:
            vis = compute_visible_ratio((x1, y1, x2, y2), occluder_rects)
            if vis >= MIN_VISIBLE:
                filtered.append((cid, x1, y1, x2, y2))
        projected = filtered

    # --- skenario khusus: perspective ------------------------------------
    if scenario == "perspective":
        canvas, M3 = apply_perspective_warp(canvas, strength=random.uniform(0.06, 0.15))
        projected = [
            (cid, *project_bbox_perspective((x1, y1, x2, y2), M3))
            for cid, x1, y1, x2, y2 in projected
        ]

    # --- skenario khusus: motion_blur ------------------------------------
    if scenario == "motion_blur":
        canvas = apply_motion_blur(canvas)

    # --- skenario khusus: glare_reflection --------------------------------
    if scenario == "glare_reflection":
        canvas = apply_glare(canvas, strength=random.uniform(0.35, 0.65))

    # --- skenario khusus: shadow_partial -----------------------------------
    if scenario == "shadow_partial":
        canvas = apply_shadow(canvas, strength=random.uniform(0.35, 0.6))

    # --- skenario khusus: scan_artifact -------------------------------------
    if scenario == "scan_artifact":
        canvas = apply_scan_artifact(canvas)

    # clip & filter bbox akhir ------------------------------------------
    final_labels = []
    for cid, x1, y1, x2, y2 in projected:
        cx1, cy1, cx2, cy2 = clip_bbox((x1, y1, x2, y2), canvas_w, canvas_h)
        if (cx2 - cx1) < 4 or (cy2 - cy1) < 4:
            continue
        area_ratio = bbox_area((cx1, cy1, cx2, cy2)) / max(1.0, bbox_area((x1, y1, x2, y2)))
        if area_ratio < MIN_VISIBLE and cid != CLASS_KK:
            # bbox kecil (mis. teks) yg sebagian besar terpotong tepi canvas -> drop
            continue
        yolo = xyxy_to_yolo((cx1, cy1, cx2, cy2), canvas_w, canvas_h)
        final_labels.append((cid, *yolo))

    # post-processing warna/noise/blur/jpeg (skenario dark/bright ditangani di sini juga)
    canvas = apply_postprocessing(canvas, scenario)

    return canvas, final_labels, scenario


# =====================================================================
# MAIN - generate dataset lengkap
# =====================================================================
def write_data_yaml(output_dir):
    """data.yaml dengan nc:9 dan semua nama lengkap 0-8, agar kompatibel
    untuk digabung dengan dataset KTP/SIM/Paspor/Plat Nomor yang sudah ada."""
    yaml_content = f"""# PrivAI - Dataset Kartu Keluarga (KK) synthetic
# Kompatibel dengan skema class dataset KTP/SIM/Paspor/Plat Nomor (class 0-5)
#
# PENTING - saat training YOLO, WAJIB set fliplr=0.0 (jangan mirror
# horizontal) karena teks/NIK/no.KK akan terbalik dan tidak representatif.
# Contoh:
#   from ultralytics import YOLO
#   model = YOLO('yolo11n.pt')
#   model.train(data='data.yaml', epochs=100, fliplr=0.0)

path: {os.path.abspath(output_dir)}
train: images/train
val: images/val

nc: 9
names:
  0: ktp
  1: sim
  2: paspor
  3: nik_teks
  4: wajah
  5: plat_nomor
  6: kk
  7: kartu_atm
  8: resi
"""
    with open(os.path.join(output_dir, "data.yaml"), "w") as f:
        f.write(yaml_content)


def generate_dataset(output_dir=OUTPUT_DIR, total_images=TOTAL_IMAGES, val_split=0.15):
    img_train_dir = os.path.join(output_dir, "images", "train")
    img_val_dir = os.path.join(output_dir, "images", "val")
    lbl_train_dir = os.path.join(output_dir, "labels", "train")
    lbl_val_dir = os.path.join(output_dir, "labels", "val")
    for d in (img_train_dir, img_val_dir, lbl_train_dir, lbl_val_dir):
        os.makedirs(d, exist_ok=True)
        for filename in os.listdir(d):
            if filename.startswith("kk_") and filename.lower().endswith(
                (".jpg", ".jpeg", ".png", ".txt")
            ):
                os.remove(os.path.join(d, filename))

    n_val = max(1, int(total_images * val_split))
    n_train = total_images - n_val

    scenario_cycle = SCENARIOS * (total_images // len(SCENARIOS) + 1)
    random.shuffle(scenario_cycle)

    stats = {sc: 0 for sc in SCENARIOS}
    empty_label_count = 0

    for idx in range(total_images):
        scenario = scenario_cycle[idx]
        try:
            use_qr = idx % 2 == 0
            img, labels, used_scenario = generate_sample(
                scenario=scenario,
                use_qr=use_qr,
            )
        except Exception as e:
            print(f"[WARN] gagal generate sample {idx} (skenario={scenario}): {e}")
            continue

        if not labels:
            empty_label_count += 1

        stats[used_scenario] = stats.get(used_scenario, 0) + 1

        split = "val" if idx < n_val else "train"
        img_dir = img_val_dir if split == "val" else img_train_dir
        lbl_dir = lbl_val_dir if split == "val" else lbl_train_dir

        format_name = "qr" if use_qr else "legacy"
        fname = f"kk_{idx:05d}_{format_name}_{used_scenario}"
        img_path = os.path.join(img_dir, fname + ".jpg")
        lbl_path = os.path.join(lbl_dir, fname + ".txt")

        cv2.imwrite(img_path, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(lbl_path, "w") as f:
            for cid, cx, cy, w, h in labels:
                f.write(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        if (idx + 1) % max(1, total_images // 10) == 0 or idx == total_images - 1:
            print(f"  [{idx+1}/{total_images}] generated (scenario={used_scenario}, n_labels={len(labels)})")

    write_data_yaml(output_dir)

    print("\n=== Ringkasan Generasi Dataset KK ===")
    print(f"Total gambar diminta : {total_images}")
    print(f"Train / Val split    : {n_train} / {n_val}")
    print(f"Gambar tanpa label   : {empty_label_count}")
    print("Distribusi skenario  :")
    for sc, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {sc:20s}: {cnt}")
    print(f"\nOutput disimpan di   : {os.path.abspath(output_dir)}")
    print(f"data.yaml            : {os.path.join(os.path.abspath(output_dir), 'data.yaml')}")


if __name__ == "__main__":
    print(f"Memulai generate dataset KK synthetic -> {OUTPUT_DIR}")
    print(f"Total images: {TOTAL_IMAGES}, MIN_VISIBLE: {MIN_VISIBLE}")
    generate_dataset(OUTPUT_DIR, TOTAL_IMAGES)
