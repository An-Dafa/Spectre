import random
import tempfile
from pathlib import Path

import cv2
import numpy as np

from augmentasi import JUMLAH_AUGMENTASI, SEMUA_AUGMENTASI, baca_label_yolo
from data_auditor import draw_annotations
from datagen_atm import (
    TOTAL_IMAGES as ATM_TOTAL_IMAGES,
    generate_atm_mockup,
    generate_non_luhn_card_number,
    luhn_valid,
)
from datagen_common import (
    SCENARIOS,
    apply_document_scenario,
    compute_visible_ratio,
    generate_synthetic_portrait,
    paper_border_value,
    write_data_yaml,
)
from datagen_kk import SCENARIOS as KK_SCENARIOS
from datagen_kk import (
    TOTAL_IMAGES as KK_TOTAL_IMAGES,
    gen_kk_data,
    generate_sample,
    render_kk_document,
    scale_column_widths,
)
from datagen_ktp import TOTAL_IMAGES as KTP_TOTAL_IMAGES, generate_ktp_mockup
from datagen_paspor import TOTAL_IMAGES as PASPOR_TOTAL_IMAGES, generate_paspor_mockup
from datagen_plat import TOTAL_IMAGES as PLAT_TOTAL_IMAGES, generate_plat_mockup
from datagen_resi import TOTAL_IMAGES as RESI_TOTAL_IMAGES, generate_resi_mockup
from datagen_sim import TOTAL_IMAGES as SIM_TOTAL_IMAGES, generate_sim_mockup


def assert_valid_labels(labels):
    assert labels
    for label in labels:
        assert len(label) == 5
        assert all(0 <= value <= 1 for value in label[1:])
        assert label[3] > 0 and label[4] > 0


def main():
    random.seed(7)
    np.random.seed(7)
    assert (
        KTP_TOTAL_IMAGES,
        SIM_TOTAL_IMAGES,
        PASPOR_TOTAL_IMAGES,
        PLAT_TOTAL_IMAGES,
        KK_TOTAL_IMAGES,
        ATM_TOTAL_IMAGES,
        RESI_TOTAL_IMAGES,
    ) == (800, 900, 900, 1000, 1000, 1000, 1000)
    assert JUMLAH_AUGMENTASI == {
        "ktp": 4,
        "sim": 4,
        "paspor": 4,
        "plat": 2,
        "kk": 4,
        "atm": 4,
        "resi": 4,
        "widerface": 1,
    }
    assert compute_visible_ratio.__qualname__ == "compute_visible_ratio"
    portrait, face_box = generate_synthetic_portrait(180, 220)
    assert portrait.size == (180, 220)
    assert 0 <= face_box[0] < face_box[2] <= 180
    assert 0 <= face_box[1] < face_box[3] <= 220

    for _ in range(100):
        raw, formatted = generate_non_luhn_card_number()
        assert len(raw) == 16 and raw.isdigit() and not luhn_valid(raw)
        assert formatted == " ".join(raw[index:index + 4] for index in range(0, 16, 4))

    for _ in range(100):
        blue, green, red = paper_border_value()
        assert 240 <= blue <= 255
        assert 240 <= green <= 255
        assert 235 <= red <= 250

    dummy = np.full((300, 500, 3), 190, dtype=np.uint8)
    dummy_boxes = [(7, 0, 0, 500, 300), (3, 100, 100, 350, 150)]
    for scenario in SCENARIOS:
        image, labels, used = apply_document_scenario(
            dummy, dummy_boxes, scenario=scenario
        )
        assert image is not None and used == scenario
        assert_valid_labels(labels)
        if scenario == "face_background":
            assert any(label[0] == 4 for label in labels)
        if scenario in ("stacked_docs", "scattered_cards"):
            assert sum(label[0] == 7 for label in labels) >= 2

    generators = [
        ("ktp", generate_ktp_mockup, {0, 3, 4}, 15),
        ("sim", generate_sim_mockup, {1, 3, 4}, 8),
        ("paspor", generate_paspor_mockup, {2, 3, 4}, 11),
        ("plat", generate_plat_mockup, {3, 5}, 2),
    ]
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name, generator, expected_classes, min_sensitive in generators:
            image_dir = root / name / "images"
            label_dir = root / name / "labels"
            generator(str(image_dir), str(label_dir), 0, scenario="normal")
            image_path = next(image_dir.glob("*.jpg"))
            label_path = next(label_dir.glob("*.txt"))
            image = cv2.imread(str(image_path))
            labels = baca_label_yolo(label_path)
            assert image is not None
            assert {label[0] for label in labels} == expected_classes
            assert sum(label[0] == 3 for label in labels) >= min_sensitive
            if name in ("ktp", "sim", "paspor"):
                face_count = sum(label[0] == 4 for label in labels)
                assert 1 <= face_count <= (2 if name == "sim" else 1)
            assert_valid_labels(labels)
            _, annotation_count = draw_annotations(image, label_path, {})
            assert annotation_count == len(labels)

        for feature, expected_faces, min_sensitive in (
            ("qr", 1, 9),
            ("fingerprint", 1, 9),
            ("ghost_portrait", 2, 8),
        ):
            _, labels = generate_sim_mockup(
                str(root / "sim_features" / "images"),
                str(root / "sim_features" / "labels"),
                feature,
                scenario="normal",
                security_feature=feature,
            )
            assert sum(label[0] == 4 for label in labels) == expected_faces
            assert sum(label[0] == 3 for label in labels) >= min_sensitive

        for side_mode in ("front", "back", "both"):
            image, labels = generate_atm_mockup(
                str(root / "atm" / "images"),
                str(root / "atm" / "labels"),
                side_mode,
                scenario="normal",
                side_mode=side_mode,
            )
            assert image is not None
            assert any(label[0] == 3 for label in labels)
            expected_cards = 2 if side_mode == "both" else 1
            assert sum(label[0] == 7 for label in labels) == expected_cards
            assert_valid_labels(labels)

        for orientation in ("portrait", "landscape"):
            for scenario in ("normal", "thermal_fade", "rolled_warp", "folded"):
                image, labels = generate_resi_mockup(
                    str(root / "resi" / "images"),
                    str(root / "resi" / "labels"),
                    f"{orientation}_{scenario}",
                    scenario=scenario,
                    orientation=orientation,
                )
                assert image is not None
                assert any(label[0] == 8 for label in labels)
                assert any(label[0] == 3 for label in labels)
                assert_valid_labels(labels)

        write_data_yaml(root / "yaml")
        yaml_text = (root / "yaml" / "data.yaml").read_text(encoding="utf-8")
        assert "fliplr=0.0" in yaml_text

    image = np.full((480, 640, 3), 180, dtype=np.uint8)
    labels = [[3, 0.5, 0.5, 0.4, 0.2]]
    for augmentation in SEMUA_AUGMENTASI:
        augmented, augmented_labels = augmentation(
            image.copy(), [row[:] for row in labels]
        )
        assert augmented.shape == image.shape
        assert len(augmented_labels) == len(labels)
        assert_valid_labels(augmented_labels)

    _, document_boxes = render_kk_document(gen_kk_data(1))
    assert sum(scale_column_widths([30, 150, 130], 1184)) == 1184
    assert sum(box[0] == 3 for box in document_boxes) >= 28
    for use_qr in (True, False):
        kk_data = gen_kk_data(4)
        kk_data["use_qr"] = use_qr
        kk_image, _ = render_kk_document(kk_data)
        right_footer = np.array(kk_image)[650:835, 930:1215]
        assert np.count_nonzero(right_footer.mean(axis=2) < 180) > 250
    assert KK_SCENARIOS == SCENARIOS
    for scenario in KK_SCENARIOS:
        image, labels, used_scenario = generate_sample(scenario)
        assert image is not None and used_scenario == scenario
        assert any(label[0] == 6 for label in labels)
        assert any(label[0] == 3 for label in labels)
        assert_valid_labels(labels)

    print("OK: generator, skenario, ATM non-Luhn/dua sisi, resi thermal/warp, dan bbox lulus")


if __name__ == "__main__":
    main()
