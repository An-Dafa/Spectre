from dataclasses import dataclass

from fastapi import HTTPException, status


CANONICAL_CLASSES = ["KTP", "KK", "SIM", "Paspor", "Teks_Sensitif", "Wajah", "Plat_Nomor", "Resi"]

_CLASS_ALIASES = {
    "ktp": "KTP",
    "kartu_tanda_penduduk": "KTP",
    "kartu tanda penduduk": "KTP",
    "kk": "KK",
    "kartu_keluarga": "KK",
    "kartu keluarga": "KK",
    "sim": "SIM",
    "surat_izin_mengemudi": "SIM",
    "surat izin mengemudi": "SIM",
    "paspor": "Paspor",
    "passport": "Paspor",
    "nik": "Teks_Sensitif",
    "nik_teks": "Teks_Sensitif",
    "nik teks": "Teks_Sensitif",
    "nik_text": "Teks_Sensitif",
    "nik text": "Teks_Sensitif",
    "teks_sensitif": "Teks_Sensitif",
    "teks sensitif": "Teks_Sensitif",
    "teks_sensitive": "Teks_Sensitif",
    "teks sensitive": "Teks_Sensitif",
    "sensitive_text": "Teks_Sensitif",
    "sensitive text": "Teks_Sensitif",
    "wajah": "Wajah",
    "face": "Wajah",
    "plat_nomor": "Plat_Nomor",
    "plat nomor": "Plat_Nomor",
    "plat": "Plat_Nomor",
    "license_plate": "Plat_Nomor",
    "license plate": "Plat_Nomor",
    "resi": "Resi",
    "shipping_label": "Resi",
    "shipping label": "Resi",
    "label_pengiriman": "Resi",
    "label pengiriman": "Resi",
    "receipt": "Resi",
}


@dataclass(frozen=True)
class ClassInfo:
    name: str
    risk_level: str
    description: str


CLASS_INFO = {
    "KTP": ClassInfo("KTP", "critical", "Dokumen identitas kependudukan."),
    "KK": ClassInfo("KK", "critical", "Kartu keluarga yang memuat data anggota keluarga."),
    "SIM": ClassInfo("SIM", "critical", "Dokumen izin mengemudi yang memuat identitas."),
    "Paspor": ClassInfo("Paspor", "critical", "Dokumen perjalanan yang memuat identitas legal."),
    "Teks_Sensitif": ClassInfo("Teks_Sensitif", "critical", "Nomor identitas, alamat, rekening, nomor telepon, atau teks sensitif lain."),
    "Wajah": ClassInfo("Wajah", "high", "Wajah pengguna atau pihak ketiga dalam citra."),
    "Plat_Nomor": ClassInfo("Plat_Nomor", "medium", "Nomor kendaraan yang dapat menjadi identifier."),
    "Resi": ClassInfo("Resi", "high", "Label pengiriman yang dapat memuat nama, alamat, dan nomor telepon."),
}


def normalize_class_name(value: str) -> str:
    key = value.strip().replace("-", "_")
    normalized_key = key.lower()
    if key in CANONICAL_CLASSES:
        return key
    if normalized_key in _CLASS_ALIASES:
        return _CLASS_ALIASES[normalized_key]
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown class name: {value}",
    )


def parse_class_csv(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    classes: list[str] = []
    for item in value.split(","):
        if item.strip():
            class_name = normalize_class_name(item)
            if class_name not in classes:
                classes.append(class_name)
    return classes


def serialize_classes() -> list[dict[str, str]]:
    return [
        {
            "name": info.name,
            "risk_level": info.risk_level,
            "description": info.description,
        }
        for info in CLASS_INFO.values()
    ]
