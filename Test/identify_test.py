import numpy as np
import pytest

from identify import identify_page, RATIO_TOLERANCE
from image_prep import prepare_pages
from layout import PAGE_SIZES


def blank_table(width, height):
    """A fake all-white table of the given size. identify_page only looks at
    the shape, so the content doesn't matter."""
    return np.full((height, width), 255, dtype=np.uint8)


# ---------- Exact template sizes ----------

def test_page1_template_size():
    w, h = PAGE_SIZES[1]
    assert identify_page(blank_table(w, h)) == 1


def test_page2_template_size():
    w, h = PAGE_SIZES[2]
    assert identify_page(blank_table(w, h)) == 2


# ---------- Real scans (the blank forms) ----------

def test_real_blank_forms():
    pages = prepare_pages(["blank_01.pdf", "blank_02.pdf"])
    assert [identify_page(table) for source, page, table in pages] == [1, 2]


# ---------- Small differences between scans ----------

def test_slightly_off_sizes_still_work():
    assert identify_page(blank_table(2741, 1389)) == 1
    assert identify_page(blank_table(2730, 912)) == 2


# ---------- Different resolutions (why we use the ratio) ----------

@pytest.mark.parametrize("scale", [0.5, 2 / 3, 1.5, 2.0])   # 150, 200, 450, 600 dpi
def test_any_resolution(scale):
    for page, (w, h) in PAGE_SIZES.items():
        table = blank_table(round(w * scale), round(h * scale))
        assert identify_page(table) == page


# ---------- Shapes that match neither page ----------

def test_square_raises():
    with pytest.raises(ValueError):
        identify_page(blank_table(100, 100))


def test_whole_page_instead_of_table_raises():
    # If table detection failed and we got the whole upright page (3300 x 2550)
    with pytest.raises(ValueError):
        identify_page(blank_table(3300, 2550))


def test_shape_between_the_two_pages_raises():
    # Ratio 2.5: about halfway between page 1 (~2) and page 2 (~3)
    with pytest.raises(ValueError):
        identify_page(blank_table(2500, 1000))


# ---------- Edge of the tolerance ----------

def test_just_inside_tolerance_accepted():
    w, h = PAGE_SIZES[1]
    ratio = (w / h) * (1 + RATIO_TOLERANCE - 0.01)     # 14% wider-shaped
    assert identify_page(blank_table(round(h * ratio), h)) == 1


def test_just_outside_tolerance_raises():
    w, h = PAGE_SIZES[1]
    ratio = (w / h) * (1 - RATIO_TOLERANCE - 0.01)     # 16% narrower-shaped
    with pytest.raises(ValueError):
        identify_page(blank_table(round(h * ratio), h))