import argparse
import random
from pathlib import Path

import cv2


MY_CLASSES = {
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

COLORS = [
    (0, 255, 0),
    (255, 0, 0),
    (0, 0, 255),
    (255, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
    (0, 165, 255),
    (255, 128, 0),
    (128, 0, 255),
]


def find_images(img_dir):
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return sorted(
        path for path in Path(img_dir).iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    )


def draw_annotations(img, label_path, class_names):
    height, width = img.shape[:2]
    if not label_path.exists():
        cv2.putText(
            img,
            "LABEL TIDAK DITEMUKAN",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )
        return img, 0

    count = 0
    with label_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 5:
                print(f"[WARN] {label_path}:{line_number} bukan format YOLO 5 kolom")
                continue
            try:
                class_id = int(parts[0])
                xc, yc, box_w, box_h = map(float, parts[1:])
            except ValueError:
                print(f"[WARN] {label_path}:{line_number} berisi nilai tidak valid")
                continue

            x1 = round((xc - box_w / 2) * width)
            y1 = round((yc - box_h / 2) * height)
            x2 = round((xc + box_w / 2) * width)
            y2 = round((yc + box_h / 2) * height)
            x1, x2 = sorted((max(0, x1), min(width - 1, x2)))
            y1, y2 = sorted((max(0, y1), min(height - 1, y2)))
            if x2 <= x1 or y2 <= y1:
                print(f"[WARN] {label_path}:{line_number} bbox kosong/di luar gambar")
                continue

            color = COLORS[class_id % len(COLORS)]
            name = class_names.get(class_id, f"class_{class_id}")
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            text_y = y1 - 8 if y1 >= 22 else y1 + 18
            cv2.putText(
                img,
                name,
                (x1, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )
            count += 1
    return img, count


def rotate_view(img, turns):
    turns %= 4
    if turns == 1:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if turns == 2:
        return cv2.rotate(img, cv2.ROTATE_180)
    if turns == 3:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img


def render_view(img, zoom, turns, filename, index, total, box_count):
    view = rotate_view(img, turns)
    height, width = view.shape[:2]
    view = cv2.resize(
        view,
        (max(1, round(width * zoom)), max(1, round(height * zoom))),
        interpolation=cv2.INTER_CUBIC if zoom > 1 else cv2.INTER_AREA,
    )
    status = (
        f"{index + 1}/{total} | {filename} | bbox={box_count} | "
        f"zoom={zoom:.0%} | rotate={turns * 90} deg"
    )
    cv2.rectangle(view, (0, 0), (min(view.shape[1], 1100), 32), (25, 25, 25), -1)
    cv2.putText(
        view,
        status,
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return view


def audit_dataset(img_dir, label_dir, class_names=MY_CLASSES, num_samples=50):
    images = find_images(img_dir)
    if not images:
        raise FileNotFoundError(f"Tidak ada gambar di: {Path(img_dir).resolve()}")
    if num_samples and len(images) > num_samples:
        images = random.sample(images, num_samples)

    window = "Audit Dataset PrivAI"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 1280, 800)

    index = 0
    zoom = 0.5
    turns = 0
    cache = {}

    def mouse(event, _x, _y, flags, _param):
        nonlocal zoom
        if event == cv2.EVENT_MOUSEWHEEL:
            zoom = min(4.0, zoom * 1.2) if flags > 0 else max(0.1, zoom / 1.2)

    cv2.setMouseCallback(window, mouse)
    print("Kontrol: +/- atau scroll=zoom, R/L=rotate, N/Space=berikutnya, P=sebelumnya, Q=keluar")

    while True:
        path = images[index]
        if path not in cache:
            image = cv2.imread(str(path))
            if image is None:
                print(f"[WARN] Gagal membaca {path}")
                index = (index + 1) % len(images)
                continue
            cache[path] = draw_annotations(
                image,
                Path(label_dir) / f"{path.stem}.txt",
                class_names,
            )

        annotated, box_count = cache[path]
        cv2.imshow(
            window,
            render_view(annotated, zoom, turns, path.name, index, len(images), box_count),
        )
        key = cv2.waitKeyEx(30)
        if key < 0:
            continue
        key &= 0xFF
        if key in (ord("q"), 27):
            break
        if key in (ord("+"), ord("=")):
            zoom = min(4.0, zoom * 1.2)
        elif key in (ord("-"), ord("_")):
            zoom = max(0.1, zoom / 1.2)
        elif key == ord("r"):
            turns = (turns + 1) % 4
        elif key == ord("l"):
            turns = (turns - 1) % 4
        elif key in (ord("n"), ord(" "), 13):
            index = (index + 1) % len(images)
        elif key == ord("p"):
            index = (index - 1) % len(images)
        elif key == ord("0"):
            zoom, turns = 0.5, 0

    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Viewer/auditor anotasi YOLO")
    parser.add_argument(
        "images",
        nargs="?",
        default="datasets/atm_synth/images/train",
        help="Folder gambar",
    )
    parser.add_argument(
        "labels",
        nargs="?",
        default="datasets/atm_synth/labels/train",
        help="Folder label YOLO",
    )
    parser.add_argument("--samples", type=int, default=15, help="0 = semua gambar")
    args = parser.parse_args()
    audit_dataset(args.images, args.labels, num_samples=args.samples)


if __name__ == "__main__":
    main()
