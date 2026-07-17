import pymupdf

from app.utils.image_utils import read_document_bytes_to_cv2


def make_pdf(page_count: int) -> bytes:
    document = pymupdf.open()
    for _ in range(page_count):
        page = document.new_page(width=200, height=100)
        page.insert_text((20, 50), "Spectre")
    data = document.tobytes()
    document.close()
    return data


def test_single_page_pdf_renders() -> None:
    image = read_document_bytes_to_cv2(make_pdf(1), "document.pdf")
    assert image.shape[0] > 0
    assert image.shape[1] > 0
    assert image.shape[2] == 3


def test_multi_page_pdf_renders_all_pages() -> None:
    image = read_document_bytes_to_cv2(make_pdf(2), "document.pdf")

    assert image.shape[0] > image.shape[1]
    assert image.shape[2] == 3


if __name__ == "__main__":
    test_single_page_pdf_renders()
    test_multi_page_pdf_renders_all_pages()
