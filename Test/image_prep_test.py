import cv2
import fitz
import numpy as np
import pytest

from itertools import permutations

from image_prep import (image_converter, load_pages, to_gray, rotate_upright,
                        prepare_pages, threshold, find_table_corners, order_corners)

# ---------- Fixtures (shared setup) ----------

@pytest.fixture(scope="module")
def gray_blank():
    """The blank form, first page, grayscale (still sideways)."""
    source, img = load_pages(["blank_01.pdf"])[0]
    return to_gray(img)


@pytest.fixture(scope="module")
def upright_blank(gray_blank):
    """The blank form after rotate_upright."""
    return rotate_upright(gray_blank)


@pytest.fixture
def two_page_pdf(tmp_path):
    """A fake 2-page PDF built on the fly (no real scan needed)."""
    path = tmp_path / "two_pages.pdf"
    with fitz.open() as doc:                   # fitz.open() with no args = new empty PDF
        doc.new_page()
        doc.new_page()
        doc.save(path)
    return path


# ---------- image_converter ----------

def test_converter_returns_one_path_per_page(tmp_path):
    paths = image_converter("blank_01.pdf", out_dir=tmp_path)
    assert len(paths) == 1
    assert paths[0].exists()


def test_converter_output_name(tmp_path):
    paths = image_converter("blank_01.pdf", out_dir=tmp_path)
    assert paths[0].name == "blank_01_p1.png"


def test_converter_output_is_readable_image(tmp_path):
    paths = image_converter("blank_01.pdf", out_dir=tmp_path)
    assert cv2.imread(str(paths[0])) is not None


def test_converter_resolution_300dpi(tmp_path):
    paths = image_converter("blank_01.pdf", out_dir=tmp_path)
    img = cv2.imread(str(paths[0]))
    assert img.shape == (3300, 2550, 3)        # letter page at 300 dpi


def test_converter_two_page_pdf(two_page_pdf, tmp_path):
    paths = image_converter(two_page_pdf, out_dir=tmp_path / "out")
    assert [p.name for p in paths] == ["two_pages_p1.png", "two_pages_p2.png"]


def test_converter_missing_pdf_raises(tmp_path):
    # PyMuPDF's own FileNotFoundError is a subclass of RuntimeError
    with pytest.raises(RuntimeError):
        image_converter("does_not_exist.pdf", out_dir=tmp_path)


# ---------- load_pages ----------

def test_load_pdf_returns_color_page():
    pages = load_pages(["blank_01.pdf"])
    assert len(pages) == 1
    source, img = pages[0]
    assert source == "blank_01.pdf p1"
    assert img.ndim == 3 and img.shape[2] == 3


def test_load_single_name_shortcut():
    assert len(load_pages("blank_01.pdf")) == 1


def test_load_two_page_pdf(two_page_pdf):
    pages = load_pages([two_page_pdf])
    assert [src for src, img in pages] == ["two_pages.pdf p1", "two_pages.pdf p2"]


def test_load_keeps_upload_order(two_page_pdf):
    # blank (1 page) then the fake PDF (2 pages) -> 3 pages, in that order
    pages = load_pages(["blank_01.pdf", two_page_pdf])
    assert [src for src, img in pages] == [
        "blank_01.pdf p1", "two_pages.pdf p1", "two_pages.pdf p2"]


def test_load_mixed_pdf_and_png(tmp_path):
    png = tmp_path / "page.png"
    cv2.imwrite(str(png), np.full((100, 200, 3), 255, dtype=np.uint8))
    pages = load_pages(["blank_01.pdf", png])
    assert [src for src, img in pages] == ["blank_01.pdf p1", "page.png"]


def test_load_unsupported_type_raises():
    with pytest.raises(ValueError):
        load_pages(["notes.txt"])


def test_load_missing_png_raises():
    with pytest.raises(FileNotFoundError):
        load_pages(["missing.png"])


# ---------- to_gray ----------

def test_gray_has_two_dimensions(gray_blank):
    assert gray_blank.ndim == 2


def test_gray_keeps_size():
    source, img = load_pages(["blank_01.pdf"])[0]
    assert to_gray(img).shape == img.shape[:2]


# ---------- rotate_upright ----------

def test_upright_is_landscape(upright_blank):
    h, w = upright_blank.shape
    assert w > h


@pytest.mark.parametrize("code", [
    cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_180,
    cv2.ROTATE_90_COUNTERCLOCKWISE,
])
def test_all_orientations_give_same_result(gray_blank, upright_blank, code):
    rotated_input = cv2.rotate(gray_blank, code)
    assert np.array_equal(rotate_upright(rotated_input), upright_blank)


def test_already_upright_is_unchanged(upright_blank):
    assert np.array_equal(rotate_upright(upright_blank), upright_blank)


def test_fake_image_dark_bottom_gets_flipped():
    fake = np.full((300, 400), 255, dtype=np.uint8)   # all white, landscape
    fake[-40:, :] = 0                                 # black band at the bottom
    result = rotate_upright(fake)
    assert result[:40, :].mean() == 0                 # band is now at the top
    assert result[-40:, :].mean() == 255              # bottom is white


# ---------- prepare_pages ----------

def test_prepare_returns_upright_gray_pages():
    pages = prepare_pages(["blank_01.pdf", "blank_02.pdf"])
    assert [src for src, img in pages] == ["blank_01.pdf p1", "blank_02.pdf p1"]
    for src, img in pages:
        assert img.ndim == 2                 # grayscale
        h, w = img.shape
        assert w > h                         # upright = landscape


def test_prepare_debug_dir_saves_images(tmp_path):
    prepare_pages(["blank_01.pdf"], debug_dir=tmp_path)
    assert (tmp_path / "blank_01_pdf_p1_upright.png").exists()



# ----------  threshold / find table / order corners ----------

@pytest.fixture(scope="module")
def upright_pages():
    """Both blank pages, upright gray, as {source: image}."""
    return {src: rotate_upright(to_gray(img))
            for src, img in load_pages(["blank_01.pdf", "blank_02.pdf"])}


def test_threshold_only_black_and_white(upright_pages):
    binary = threshold(upright_pages["blank_01.pdf p1"])
    assert set(np.unique(binary)) <= {0, 255}


def test_threshold_ink_is_white(upright_pages):
    # A blank form is mostly paper, so most pixels should be black (0)
    binary = threshold(upright_pages["blank_01.pdf p1"])
    assert (binary == 255).mean() < 0.5


def test_threshold_keeps_size(upright_pages):
    gray = upright_pages["blank_01.pdf p1"]
    assert threshold(gray).shape == gray.shape


def test_finds_four_corners_on_both_pages(upright_pages):
    for gray in upright_pages.values():
        assert find_table_corners(threshold(gray)).shape == (4, 2)


def test_page1_table_corners(upright_pages):
    c = order_corners(find_table_corners(threshold(upright_pages["blank_01.pdf p1"])))
    expected = [[300, 478], [3037, 468], [3042, 1860], [305, 1870]]
    assert np.allclose(c, expected, atol=10)      # within 10 px


def test_page1_and_page2_table_shapes(upright_pages):
    def ratio(gray):
        tl, tr, br, bl = order_corners(find_table_corners(threshold(gray)))
        return np.linalg.norm(tr - tl) / np.linalg.norm(bl - tl)   # width / height
    assert 1.8 < ratio(upright_pages["blank_01.pdf p1"]) < 2.2     # page 1 ≈ 2
    assert 2.8 < ratio(upright_pages["blank_02.pdf p1"]) < 3.2     # page 2 ≈ 3


def test_fake_tilted_rectangle_corners():
    # Draw a slightly crooked white rectangle on black and check we find it
    img = np.zeros((500, 800), dtype=np.uint8)
    pts = np.array([[105, 100], [700, 90], [705, 400], [110, 410]], dtype=np.int32)
    cv2.polylines(img, [pts], isClosed=True, color=255, thickness=8)
    c = order_corners(find_table_corners(img))
    assert np.allclose(c, pts, atol=8)


def test_blank_page_raises():
    with pytest.raises(ValueError):
        find_table_corners(np.zeros((300, 400), dtype=np.uint8))


def test_small_shape_raises():
    img = np.zeros((300, 400), dtype=np.uint8)
    cv2.rectangle(img, (10, 10), (40, 40), 255, -1)   # tiny filled square
    with pytest.raises(ValueError):
        find_table_corners(img)


def test_order_corners_any_input_order():
    pts = [[100, 0], [0, 0], [0, 50], [100, 50]]
    for shuffled in permutations(pts):
        assert order_corners(list(shuffled)).tolist() == [[0, 0], [100, 0], [100, 50], [0, 50]]