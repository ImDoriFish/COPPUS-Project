import numpy as np
import pytest

from extract import cell_box, ink_fraction, measure_page, read_page, CODE_NAMES
from layout import INTERVALS


# ---------- CODE_NAMES ----------

def test_code_names():
    names = [name for _, name in CODE_NAMES]
    assert len(names) == 30                                  # 15 student + 12 instructor + 3 engagement
    assert names[:6] == ["S_L", "S_Ind", "S_Fol", "S_CG", "S_WG", "S_C"]    # new code C
    assert CODE_NAMES[15] == (16, "I_Lec")
    assert CODE_NAMES[-1] == (30, "E_H")
    assert len(set(names)) == 30                             # no duplicates (AnQ, W, O are prefixed)


# ---------- cell_box ----------

FAKE_PAGE = {"row_lines": [0, 40, 140], "col_lines": [0, 50, 110, 170]}


def test_cell_box_uses_the_page_lines():
    assert cell_box(FAKE_PAGE, 1, 1, margin=0) == (50, 40, 110, 140)


def test_cell_box_margin_shrinks_every_side():
    assert cell_box(FAKE_PAGE, 1, 1, margin=10) == (60, 50, 100, 130)


# ---------- ink_fraction ----------

def test_ink_fraction_empty_and_full():
    binary = np.zeros((140, 170), dtype=np.uint8)
    assert ink_fraction(binary, FAKE_PAGE, 1, 1, ) == 0.0
    binary[40:140, 50:110] = 255                             # fill that whole cell with ink
    assert ink_fraction(binary, FAKE_PAGE, 1, 1) == 1.0


# ---------- on the real blank forms ----------

def test_blank_boxes_are_empty(blank_pages):
    # CELL_MARGIN must keep the grid lines out: no ink in any box of a blank form
    for page in blank_pages.values():
        assert max(measure_page(page).values()) < 0.01


def test_read_page_on_blank(blank_pages):
    page = blank_pages["blank_80.pdf p3"]                    # 80-min LAST page
    rows = read_page(page, INTERVALS[80][3])
    assert [r["interval"] for r in rows] == INTERVALS[80][3]   # "60-62" ... "78-80", in order
    assert all(len(r) == 31 for r in rows)                   # "interval" + 30 codes
    assert sum(v for r in rows for k, v in r.items() if k != "interval") == 0   # nothing checked


def test_read_page_wrong_number_of_labels_raises(blank_pages):
    page = blank_pages["blank_80.pdf p3"]                    # 10 interval rows
    with pytest.raises(ValueError, match="blank_80.pdf p3: 10 interval rows but 15 labels"):
        read_page(page, INTERVALS[80][1])                    # page 1's 15 labels
