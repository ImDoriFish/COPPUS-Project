import cv2
import numpy as np
from layout import (ROW_LINES, COL_LINES, INTERVAL_ROWS, INTERVALS,
                    STUDENT, INSTRUCTOR, ENGAGEMENT,
                    STUDENT_COLS, INSTRUCTOR_COLS, ENGAGEMENT_COLS)
from image_prep import threshold

# Threshold of how much ink inside of a check box
CHECK_THRESHOLD = 0.03

# All columns that hold checkboxes, left to right
CODE_COLS = STUDENT_COLS + INSTRUCTOR_COLS + ENGAGEMENT_COLS

# How many pixels to shrink each cell on every side, so the box stays
# inside the cell and doesn't include the grid lines.
CELL_MARGIN = 12

CODE_NAMES = []

# Student codes: columns 1-14
for i in range(len(STUDENT)):
    col  = STUDENT_COLS[i]          # e.g. 1
    code = STUDENT[i]               # e.g. "L"
    CODE_NAMES.append((col, "S_" + code))      # → (1, "S_L")

# Instructor codes: columns 15-26
for i in range(len(INSTRUCTOR)):
    CODE_NAMES.append((INSTRUCTOR_COLS[i], "I_" + INSTRUCTOR[i]))   # → (15, "I_Lec")

# Engagement codes: columns 27-29
for i in range(len(ENGAGEMENT)):
    CODE_NAMES.append((ENGAGEMENT_COLS[i], "E_" + ENGAGEMENT[i]))   # → (27, "E_L")

# ---------- dectect grid boxes ----------
def cell_box(page, row, col, margin=CELL_MARGIN):
    """Turn a row and column number into the cell's pixel box.

    Row r is between ROW_LINES[page][r] and ROW_LINES[page][r + 1];
    column c is between COL_LINES[page][c] and COL_LINES[page][c + 1].
    Each side is moved `margin` pixels inward to stay off the grid lines.

    Returns (x0, y0, x1, y1): top-left corner and bottom-right corner.
    Example: cell_box(1, 2, 1, margin=0) -> (66, 74, 129, 157)
    """
    #top left
    x0 = COL_LINES[page][col] + margin
    y0 = ROW_LINES[page][row] + margin

    #top right
    x1 = COL_LINES[page][col + 1] - margin
    y1 = ROW_LINES[page][row + 1] - margin

    return x0, y0, x1, y1

def draw_cells(table, page):
    """Debug picture: a red rectangle inside every checkbox cell.

    table: a prepared (gray, normalized) table from prepare_pages
    page:  1 or 2

    Returns a NEW color image - the original table is not changed.
    """
    picture = cv2.cvtColor(table, cv2.COLOR_GRAY2BGR)    # color copy to draw on

    for row in INTERVAL_ROWS[page]:          # every interval row (label rows skipped)
        for col in CODE_COLS:                # every checkbox column
            x0, y0, x1, y1 = cell_box(page, row, col)
            cv2.rectangle(picture, (x0, y0), (x1, y1), (0, 0, 255), 3)   # red (BGR!), 3 px

    return picture

def ink_fraction(binary, page, row, col):
    """How much of one checkbox is ink, from 0.0 (empty) to 1.0 (all ink).

    binary: the WHOLE table after threshold() - ink = 255, paper = 0.
            (Threshold once per page, then call this for each box.)
    page:   1 or 2
    row:    row number (from INTERVAL_ROWS), e.g. 3 = interval 2-4 on page 1
    col:    column number (from CODE_COLS),   e.g. 1 = student L

    Empty box -> about 0.00.   Box with an X -> about 0.10-0.25.
    """
    x0, y0, x1, y1 = cell_box(page, row, col)   # where the box is (margin keeps grid lines out)
    cell = binary[y0:y1, x0:x1]                  # cut it out - rows (y) first, then columns (x)
    ink_pixels = np.count_nonzero(cell == 255)
    total_pixels = cell.size

    fraction = ink_pixels / total_pixels

    return fraction

def measure_page(table, page):
    """Measure the ink in EVERY checkbox on one page.

    table: a prepared (gray, normalized) table from prepare_pages
    page:  1 or 2

    Thresholds the table once, then calls ink_fraction for each box.
    Returns a dict {(row, col): ink fraction}, e.g. {(2, 1): 0.0, (3, 1): 0.123, ...}
    """
    binary = threshold(table)            # ONCE for the whole page

    fractions = {}
    for row in INTERVAL_ROWS[page]:      # every interval row (label rows skipped)
        for col in CODE_COLS:            # every checkbox column
            fractions[(row, col)] = ink_fraction(binary, page, row, col)

    return fractions

def read_page(table, page):
    """Read every checkbox on one page: 1 = checked, 0 = empty.

    table: a prepared (gray, normalized) table from prepare_pages
    page:  1 or 2

    Returns one dict per interval, top to bottom, e.g.
      [{"interval": "0-2", "S_L": 0, "S_Ind": 0, ..., "E_H": 0},
       {"interval": "2-4", "S_L": 1, ...},
       ...]
    """
    fractions = measure_page(table, page)          # ink in every box: {(row, col): fraction}

    rows = []

    for i in range(len(INTERVAL_ROWS[page])):
        row      = INTERVAL_ROWS[page][i]     # row number, e.g. 2
        interval = INTERVALS[page][i]         # its label,  e.g. "0-2"

        result = {"interval": interval}       # start this interval's dictionary

        for col, name in CODE_NAMES:          # go through all 29 (column, name) pairs
            fraction = fractions[(row, col)]  # how much ink is in this box
            if fraction > CHECK_THRESHOLD:
                result[name] = 1              # checked
            else:
                result[name] = 0              # empty

        rows.append(result)                   # add this interval's finished dictionary

    return rows


def draw_results(table, page):
    """Debug picture of what read_page decided, to compare with the paper.

    Green box = checked (ink above CHECK_THRESHOLD), red box = empty.
    Every X on the paper should be green; everything else red.

    Returns a NEW color image - the original table is not changed.
    """
    fractions = measure_page(table, page)                  # ink in every box
    picture = cv2.cvtColor(table, cv2.COLOR_GRAY2BGR)      # color copy to draw on

    rows = read_page(table, page)                          # the real results
    picture = cv2.cvtColor(table, cv2.COLOR_GRAY2BGR)      # color copy to draw on

    # Walk read_page's results in the same order it built them:
    # each result dict belongs to one interval row, each name to one column.
    for i in range(len(rows)):
        row    = INTERVAL_ROWS[page][i]     # row number of this interval, e.g. 2
        result = rows[i]                    # e.g. {"interval": "0-2", "S_L": 0, ...}

        for col, name in CODE_NAMES:        # (1, "S_L"), (2, "S_Ind"), ...
            x0, y0, x1, y1 = cell_box(page, row, col)
            if result[name] == 1:
                color = (0, 200, 0)         # green (BGR) = checked
            else:
                color = (0, 0, 255)         # red   (BGR) = empty
            cv2.rectangle(picture, (x0, y0), (x1, y1), color, 3)

    return picture
# ---------- Manual check ----------

if __name__ == "__main__":
    from image_prep import prepare_pages, OUT_DIR

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = prepare_pages(["blank_01.pdf", "blank_02.pdf", "filled_page.pdf"])

    # ---- Check 1: draw the boxes (look at them to check CELL_MARGIN) ----
    print(f"===== Check 1: box pictures (CELL_MARGIN = {CELL_MARGIN}) =====")
    for source, page, table in pages:
        picture = draw_cells(table, page)
        out_name = source.replace(".", "_").replace(" ", "_") + "_cells.png"
        cv2.imwrite(str(OUT_DIR / out_name), picture)

        count = len(INTERVAL_ROWS[page]) * len(CODE_COLS)
        print(f"{source} -> page {page}: drew {count} boxes -> {out_name}")

    # ---- Check 2: two boxes we know (one with an X, one empty) ----
    print("\n===== Check 2: two known boxes on filled_page.pdf page 1 =====")
    source, page, table = pages[2]          # filled_page.pdf p1
    binary = threshold(table)
    print("interval 2-4, student L   (has an X):", round(ink_fraction(binary, page, 3, 1), 3))
    print("interval 0-2, student Ind (empty):   ", round(ink_fraction(binary, page, 2, 2), 3))

    # ---- Check 3: measure every box and summarise (to choose CHECK_THRESHOLD) ----
    print("\n===== Check 3: ink in every box =====")
    for source, page, table in pages:
        values = [float(v) for v in measure_page(table, page).values()]

        empty   = [v for v in values if v < 0.01]
        unclear = [v for v in values if 0.01 <= v <= 0.05]
        checked = [v for v in values if v > 0.05]

        print(f"\n{source} -> page {page}: {len(values)} boxes")
        print(f"  empty   (< 0.01):     {len(empty):4}   biggest: {max(empty, default=0):.3f}")
        print(f"  unclear (0.01-0.05):  {len(unclear):4}   values: {sorted(round(v, 3) for v in unclear)}")
        print(f"  checked (> 0.05):     {len(checked):4}   smallest: {min(checked, default=0):.3f}")

    # ---- Check 4: read the filled pages (1 = checked, 0 = empty) ----
    print("\n===== Check 4: read_page on the filled sheet =====")
    for source, page, table in pages[2:]:          # the two filled pages
        rows = read_page(table, page)
        total = sum(value for r in rows for name, value in r.items() if name != "interval")
        print(f"\n{source} -> page {page}: {len(rows)} intervals, {total} checked boxes")
        for r in rows[:3]:                         # first 3 intervals: only the checked codes
            marked = [name for name, value in r.items() if name != "interval" and value == 1]
            print(f"  {r['interval']:>6}: {marked}")

    # ---- Check 5: result pictures (green = checked, red = empty) ----
    print("\n===== Check 5: result pictures =====")
    for source, page, table in pages[2:]:          # the two filled pages
        picture = draw_results(table, page)
        out_name = source.replace(".", "_").replace(" ", "_") + "_results.png"
        cv2.imwrite(str(OUT_DIR / out_name), picture)
        print(f"{source} -> page {page}: saved {out_name}")