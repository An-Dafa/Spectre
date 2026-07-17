"""Augmentasi gambar dan label YOLO untuk seluruh dataset PrivAI."""

import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np


JENIS_DOKUMEN = ["ktp", "sim", "paspor", "plat", "kk", "atm", "resi", "widerface"]
JUMLAH_AUGMENTASI = {
    "ktp": 4,
    "sim": 4,
    "paspor": 4,
    "plat": 2,
    "kk": 4,
    "atm": 4,
    "resi": 4,
    "widerface": 1,
}
SEED = 42
INPUT_DIR = Path("data_asli")
OUTPUT_DIR = Path("data_augmentasi")

NAMA_KELAS = {
    0: "KTP",
    1: "SIM",
    2: "Paspor",
    3: "Teks_Sensitif",
    4: "Wajah",
    5: "Plat_Nomor",
    6: "Kartu_Keluarga",
    7: "Kartu_ATM",
    8: "Resi",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def baca_label_yolo(path_label):
    labels = []
    with Path(path_label).open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 5:
                raise ValueError(f"{path_label}:{line_number} harus berisi 5 kolom")
            label = [int(parts[0]), *map(float, parts[1:])]
            if not all(0 <= value <= 1 for value in label[1:]):
                raise ValueError(f"{path_label}:{line_number} memiliki koordinat di luar 0..1")
            labels.append(label)
    return labels


def tulis_label_yolo(path_label, labels):
    path_label = Path(path_label)
    path_label.parent.mkdir(parents=True, exist_ok=True)
    with path_label.open("w", encoding="utf-8") as file:
        for class_id, xc, yc, width, height in labels:
            file.write(
                f"{class_id} {xc:.6f} {yc:.6f} {width:.6f} {height:.6f}\n"
            )


def yolo_ke_pixel(label, tinggi, lebar):
    _, xc, yc, width, height = label
    return (
        (xc - width / 2) * lebar,
        (yc - height / 2) * tinggi,
        (xc + width / 2) * lebar,
        (yc + height / 2) * tinggi,
    )


def pixel_ke_yolo(class_id, x1, y1, x2, y2, tinggi, lebar):
    x1, x2 = sorted(
        (float(np.clip(x1, 0, lebar)), float(np.clip(x2, 0, lebar)))
    )
    y1, y2 = sorted(
        (float(np.clip(y1, 0, tinggi)), float(np.clip(y2, 0, tinggi)))
    )
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    return [
        class_id,
        (x1 + x2) / 2 / lebar,
        (y1 + y2) / 2 / tinggi,
        (x2 - x1) / lebar,
        (y2 - y1) / tinggi,
    ]


def transform_labels(labels, matrix, tinggi, lebar, perspective=False):
    transformed_labels = []
    for label in labels:
        x1, y1, x2, y2 = yolo_ke_pixel(label, tinggi, lebar)
        points = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
        if perspective:
            transformed = cv2.perspectiveTransform(points.reshape(-1, 1, 2), matrix)
        else:
            transformed = cv2.transform(points.reshape(-1, 1, 2), matrix)
        transformed = transformed.reshape(-1, 2)
        new_label = pixel_ke_yolo(
            label[0],
            transformed[:, 0].min(),
            transformed[:, 1].min(),
            transformed[:, 0].max(),
            transformed[:, 1].max(),
            tinggi,
            lebar,
        )
        if new_label:
            transformed_labels.append(new_label)
    return transformed_labels


def aug_kecerahan(img, labels):
    alpha = random.uniform(0.55, 1.55)
    beta = random.randint(-45, 45)
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta), labels


def aug_rotasi(img, labels, max_derajat=15):
    tinggi, lebar = img.shape[:2]
    matrix = cv2.getRotationMatrix2D(
        (lebar / 2, tinggi / 2),
        random.uniform(-max_derajat, max_derajat),
        1.0,
    )
    result = cv2.warpAffine(
        img,
        matrix,
        (lebar, tinggi),
        borderMode=cv2.BORDER_REPLICATE,
    )
    return result, transform_labels(labels, matrix, tinggi, lebar)


def aug_blur(img, labels):
    mode = random.choice(["gaussian", "median", "none"])
    if mode == "gaussian":
        img = cv2.GaussianBlur(img, (random.choice([3, 5, 7]),) * 2, 0)
    elif mode == "median":
        img = cv2.medianBlur(img, random.choice([3, 5]))
    return img, labels


def aug_noise(img, labels):
    noise = np.random.normal(0, random.uniform(4, 22), img.shape).astype(np.float32)
    result = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return result, labels


def aug_crop(img, labels, min_rasio=0.75):
    """Crop hanya area luar bbox agar tidak menghilangkan anotasi."""
    tinggi, lebar = img.shape[:2]
    boxes = [yolo_ke_pixel(label, tinggi, lebar) for label in labels]
    min_x = max(0, int(min(box[0] for box in boxes)))
    min_y = max(0, int(min(box[1] for box in boxes)))
    max_x = min(lebar, int(max(box[2] for box in boxes)))
    max_y = min(tinggi, int(max(box[3] for box in boxes)))

    crop_x1 = random.randint(0, min_x) if min_x else 0
    crop_y1 = random.randint(0, min_y) if min_y else 0
    crop_x2 = random.randint(max_x, lebar) if max_x < lebar else lebar
    crop_y2 = random.randint(max_y, tinggi) if max_y < tinggi else tinggi
    if crop_x2 - crop_x1 < lebar * min_rasio or crop_y2 - crop_y1 < tinggi * min_rasio:
        return img, labels

    crop_w, crop_h = crop_x2 - crop_x1, crop_y2 - crop_y1
    result = cv2.resize(
        img[crop_y1:crop_y2, crop_x1:crop_x2],
        (lebar, tinggi),
        interpolation=cv2.INTER_AREA,
    )
    new_labels = []
    for label, (x1, y1, x2, y2) in zip(labels, boxes):
        new_label = pixel_ke_yolo(
            label[0],
            (x1 - crop_x1) * lebar / crop_w,
            (y1 - crop_y1) * tinggi / crop_h,
            (x2 - crop_x1) * lebar / crop_w,
            (y2 - crop_y1) * tinggi / crop_h,
            tinggi,
            lebar,
        )
        if new_label:
            new_labels.append(new_label)
    return result, new_labels


def aug_perspektif(img, labels, max_geser=0.08):
    tinggi, lebar = img.shape[:2]
    dx, dy = lebar * max_geser, tinggi * max_geser
    source = np.float32([[0, 0], [lebar, 0], [lebar, tinggi], [0, tinggi]])
    target = np.float32(
        [
            [random.uniform(0, dx), random.uniform(0, dy)],
            [lebar - random.uniform(0, dx), random.uniform(0, dy)],
            [lebar - random.uniform(0, dx), tinggi - random.uniform(0, dy)],
            [random.uniform(0, dx), tinggi - random.uniform(0, dy)],
        ]
    )
    matrix = cv2.getPerspectiveTransform(source, target)
    result = cv2.warpPerspective(
        img,
        matrix,
        (lebar, tinggi),
        borderMode=cv2.BORDER_REPLICATE,
    )
    return result, transform_labels(labels, matrix, tinggi, lebar, perspective=True)


def aug_warna(img, labels):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + random.uniform(-18, 18)) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * random.uniform(0.65, 1.35), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), labels


def aug_kompresi(img, labels):
    ok, encoded = cv2.imencode(
        ".jpg",
        img,
        [cv2.IMWRITE_JPEG_QUALITY, random.randint(35, 85)],
    )
    return (cv2.imdecode(encoded, cv2.IMREAD_COLOR) if ok else img), labels


SEMUA_AUGMENTASI = [
    aug_kecerahan,
    aug_rotasi,
    aug_blur,
    aug_noise,
    aug_crop,
    aug_perspektif,
    aug_warna,
    aug_kompresi,
]


def augmentasi_satu_gambar(img, labels):
    original_count = len(labels)
    for function in random.sample(SEMUA_AUGMENTASI, random.randint(3, 5)):
        new_img, new_labels = function(img, labels)
        if len(new_labels) == original_count:
            img, labels = new_img, new_labels
        else:
            print(f"    [skip] {function.__name__}: jumlah bbox berubah")
    return img, labels


def resolve_source_root(jenis):
    candidate = INPUT_DIR / jenis
    return candidate if candidate.exists() else None


def iter_image_label_pairs(root):
    image_root = root / "images"
    label_root = root / "labels"
    if image_root.exists() and label_root.exists():
        for image_path in sorted(image_root.rglob("*")):
            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            relative = image_path.relative_to(image_root)
            label_path = (label_root / relative).with_suffix(".txt")
            yield image_path, label_path, relative
        return

    for image_path in sorted(root.rglob("*")):
        if image_path.suffix.lower() in IMAGE_EXTENSIONS:
            yield image_path, image_path.with_suffix(".txt"), image_path.relative_to(root)


def proses_satu_dokumen(jenis):
    root = resolve_source_root(jenis)
    if root is None:
        print(f"  [skip] sumber {jenis} tidak ditemukan")
        return 0

    pairs = list(iter_image_label_pairs(root))
    if not pairs:
        print(f"  [skip] tidak ada gambar di {root}")
        return 0

    total = 0
    for image_path, label_path, relative in pairs:
        if not label_path.exists():
            print(f"  [skip] label tidak ditemukan: {label_path}")
            continue
        try:
            labels = baca_label_yolo(label_path)
        except ValueError as error:
            print(f"  [skip] {error}")
            continue
        image = cv2.imread(str(image_path))
        if image is None or not labels:
            print(f"  [skip] gambar/label kosong: {image_path}")
            continue

        subdir = relative.parent
        base = relative.stem
        image_output = OUTPUT_DIR / jenis / "images" / subdir
        label_output = OUTPUT_DIR / jenis / "labels" / subdir
        image_output.mkdir(parents=True, exist_ok=True)
        label_output.mkdir(parents=True, exist_ok=True)

        for index in range(JUMLAH_AUGMENTASI.get(jenis, 0)):
            augmented, new_labels = augmentasi_satu_gambar(image.copy(), [x[:] for x in labels])
            name = f"{base}_aug_{index:03d}"
            cv2.imwrite(
                str(image_output / f"{name}.jpg"),
                augmented,
                [cv2.IMWRITE_JPEG_QUALITY, 92],
            )
            tulis_label_yolo(label_output / f"{name}.txt", new_labels)
            total += 1
    return total


def buat_ringkasan(result):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "total_keseluruhan": sum(result.values()),
        "per_jenis": result,
        "konfigurasi": {
            "augmentasi_per_foto": JUMLAH_AUGMENTASI,
            "teknik_augmentasi": [function.__name__ for function in SEMUA_AUGMENTASI],
            "seed": SEED,
            "kelas": NAMA_KELAS,
            "fliplr_training_yolo": 0.0,
        },
    }
    with (OUTPUT_DIR / "ringkasan_dataset.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)
    with (OUTPUT_DIR / "training_config.yaml").open("w", encoding="utf-8") as file:
        file.write(
            "# Wajib 0.0: teks, nomor kartu, dan barcode tidak boleh mirror.\n"
            "fliplr: 0.0\n"
        )
    return summary


def main():
    global INPUT_DIR, OUTPUT_DIR, SEED
    parser = argparse.ArgumentParser(description="Augmentasi dataset YOLO PrivAI")
    parser.add_argument("--input", type=Path, default=INPUT_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--jumlah",
        type=int,
        help="Override jumlah augmentasi untuk semua jenis yang dipilih",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--jenis", nargs="+", default=JENIS_DOKUMEN)
    args = parser.parse_args()

    INPUT_DIR = args.input
    OUTPUT_DIR = args.output
    if args.jumlah is not None:
        for jenis in args.jenis:
            JUMLAH_AUGMENTASI[jenis] = max(0, args.jumlah)
    SEED = args.seed
    random.seed(SEED)
    np.random.seed(SEED)

    result = {}
    for jenis in args.jenis:
        print(f"[{jenis.upper()}]")
        result[jenis] = proses_satu_dokumen(jenis)
        print(f"  -> {result[jenis]} gambar")
    summary = buat_ringkasan(result)
    print(f"Selesai: {summary['total_keseluruhan']} gambar di {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
