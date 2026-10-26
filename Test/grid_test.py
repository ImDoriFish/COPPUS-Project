import numpy as np
import pytest

from grid import find_lines, tall_rows, measure_table, has_summary, has_header, page_role


# Real row lines measured on the blanks (Milestone A step 1)
FIRST_50 = [4, 40, 80, 180, 278, 377, 475, 574, 614, 707, 806, 904, 1003, 1102, 1152,
            1251, 1349, 1448, 1546, 1646]                                    # 50-min page 1
LAST_50 = [4, 44, 142, 241, 340, 438, 537, 582, 681, 780, 878, 977, 1076, 1822]   # 50-min page 2
LAST_80 = [3, 36, 74, 165, 256, 347, 438, 528, 576, 666, 757, 848, 939, 1030, 1718]  # 80-min page 3


# ---------- find_lines ----------

def test_find_lines_on_fake_grid():
    # A black image with 3 white horizontal and 4 white vertical lines (2 px thick)
    img = np.zeros((300, 400), dtype=np.uint8)
    for y in (10, 150, 290):
        img[y:y + 2, :] = 255
    for x in (10, 100, 250, 390):
        img[:, x:x + 2] = 255
    assert find_lines(img, "horizontal") == [10, 150, 290]          # 2-px line -> one position
    assert find_lines(img, "vertical") == [10, 100, 250, 390]


def test_find_lines_ignores_short_marks():
    # A short stroke (like a checkmark) is not a grid line
    img = np.zeros((300, 400), dtype=np.uint8)
    img[100:102, 50:90] = 255                                       # 40 px long
    assert find_lines(img, "horizontal") == []


# ---------- tall_rows ----------

def test_tall_rows_first_page():
    assert tall_rows(FIRST_50) == [2, 3, 4, 5, 6,  8, 9, 10, 11, 12,  14, 15, 16, 17, 18]


def test_tall_rows_last_page():
    assert tall_rows(LAST_80) == [2, 3, 4, 5, 6,  8, 9, 10, 11, 12]


def test_tall_rows_50min_last_page_has_no_title_row():
    # The 50-min LAST page has no title row, so its rows start one earlier
    assert tall_rows(LAST_50) == [1, 2, 3, 4, 5,  7, 8, 9, 10, 11]


def test_tall_rows_works_at_any_scale():
    # Same page, drawn twice as big -> same rows (rules use the median, not pixels)
    assert tall_rows([y * 2 for y in LAST_80]) == tall_rows(LAST_80)


# ---------- has_summary ----------

def test_has_summary():
    assert has_summary(LAST_50) is True
    assert has_summary(LAST_80) is True
    assert has_summary(FIRST_50) is False


# ---------- has_header ----------

CORNERS = np.array([[100, 300], [700, 300], [700, 500], [100, 500]], dtype=np.float32)  # table at y=300


def test_has_header_with_text_above():
    page = np.zeros((600, 800), dtype=np.uint8)
    page[50:250, 100:700:4] = 255          # "text": lots of ink above the table
    assert has_header(page, CORNERS) is True


def test_has_header_with_nothing_above():
    page = np.zeros((600, 800), dtype=np.uint8)
    page[300:, :] = 255                    # ink only in/below the table
    assert has_header(page, CORNERS) is False


def test_has_header_ignores_ink_beside_the_table():
    page = np.zeros((600, 800), dtype=np.uint8)
    page[50:250, 0:90] = 255               # ink in the left margin, not above the table
    assert has_header(page, CORNERS) is False


def test_has_header_table_at_very_top():
    page = np.full((600, 800), 255, dtype=np.uint8)
    top = np.array([[100, 5], [700, 5], [700, 500], [100, 500]], dtype=np.float32)
    assert has_header(page, top) is False  # no room above -> no crash, just False


# ---------- measure_table ----------

def test_measure_table_wrong_column_count_raises():
    with pytest.raises(ValueError, match="found 0 column lines, expected 35"):
        measure_table(np.zeros((500, 500), dtype=np.uint8))


# ---------- on the real blank forms ----------

EXPECTED_ROLES = {
    "blank_50.pdf p1": "FIRST",  "blank_50.pdf p2": "LAST",
    "blank_80.pdf p1": "FIRST",  "blank_80.pdf p2": "MIDDLE", "blank_80.pdf p3": "LAST",
    "blank_110.pdf p1": "FIRST", "blank_110.pdf p2": "MIDDLE",
    "blank_110.pdf p3": "MIDDLE", "blank_110.pdf p4": "LAST",
}


@pytest.mark.parametrize("source, role", EXPECTED_ROLES.items())
def test_every_blank_page(blank_pages, source, role):
    page = blank_pages[source]
    assert page["role"] == role
    assert len(page["col_lines"]) == 35
    assert len(page["interval_rows"]) == (10 if role == "LAST" else 15)


def test_page_role_wrong_row_count_raises(blank_pages):
    # A LAST page with one interval row missing (e.g. a line not found) must be an error
    page = blank_pages["blank_80.pdf p3"]
    rows = page["interval_rows"][:-1]                      # 9 instead of 10
    with pytest.raises(ValueError, match="LAST page: found 9 interval rows, expected 10"):
        page_role(page["row_lines"], rows, np.zeros((10, 10), dtype=np.uint8),
                  np.zeros((4, 2), dtype=np.float32))
