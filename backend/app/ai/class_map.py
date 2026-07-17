from dataclasses import dataclass

from fastapi import HTTPException, status


CANONICAL_CLASSES = ["KTP", "KK", "SIM", "Paspor", "Teks_Sensitif", "Wajah", "Plat_Nomor", "Kartu_ATM", "Resi"]

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
    "kartu_atm": "Kartu_ATM",
    "kartu atm": "Kartu_ATM",
    "atm_card": "Kartu_ATM",
    "atm card": "Kartu_ATM",
    "debit_card": "Kartu_ATM",
    "debit card": "Kartu_ATM",
    "bank_card": "Kartu_ATM",
    "bank card": "Kartu_ATM",
    "resi": "Resi",
    "shipping_label": "Resi",
    "shipping label": "Resi",
    "label_pengiriman": "Resi",
    "label pengiriman": "Resi",
    "receipt": "Resi",
    "atm": "Kartu_ATM",
}


@dataclass(frozen=True)
class ClassInfo:
    name: str
    risk_level: str
    description: str


CLASS_INFO = {
    "KTP": ClassInfo("KTP", "critical", "National identity document."),
    "KK": ClassInfo("KK", "critical", "Family registry document containing household member data."),
    "SIM": ClassInfo("SIM", "critical", "Driver license document containing identity data."),
    "Paspor": ClassInfo("Paspor", "critical", "Travel document containing legal identity data."),
    "Teks_Sensitif": ClassInfo("Teks_Sensitif", "critical", "Identity numbers, addresses, bank accounts, phone numbers, or other sensitive text."),
    "Wajah": ClassInfo("Wajah", "high", "User or third-party face in an image."),
    "Plat_Nomor": ClassInfo("Plat_Nomor", "medium", "Vehicle plate number that can identify a vehicle."),
    "Kartu_ATM": ClassInfo("Kartu_ATM", "critical", "Bank card that can contain card numbers and financial identity data."),
    "Resi": ClassInfo("Resi", "high", "Shipping label that can contain names, addresses, and phone numbers."),
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
