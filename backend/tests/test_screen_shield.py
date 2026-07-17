from app.api.screen import ScreenRedactionRequest, redact_screen_text


def test_screen_shield_redacts_text_identifiers() -> None:
    result = redact_screen_text(
        ScreenRedactionRequest(text="NIK 3276010101010001 phone 081234567890 gaji Rp 12.000.000")
    )

    assert "3276010101010001" not in result["redacted_text"]
    assert "081234567890" not in result["redacted_text"]
    assert "12.000.000" not in result["redacted_text"]
    assert result["redacted_count"] == 3
    assert result["storage_policy"]["operational_zone_persisted"] is False


if __name__ == "__main__":
    test_screen_shield_redacts_text_identifiers()
