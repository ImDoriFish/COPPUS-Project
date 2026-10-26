import cv2
import numpy as np
from layout import (STUDENT, INSTRUCTOR, ENGAGEMENT,
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

# Student codes: columns 1-15
for i in range(len(STUDENT)):
    col  = STUDENT_COLS[i]          # e.g. 1
    code = STUDENT[i]               # e.g. "L"
    CODE_NAMES.append((col, "S_" + code))      # → (1, "S_L")

# Instructor codes: columns 16-27
for i in range(len(INSTRUCTOR)):
    CODE_NAMES.append((INSTRUCTOR_COLS[i], "I_" + INSTRUCTOR[i]))   

# Engagement codes: columns 28-30
for i in range(len(ENGAGEMENT)):
    CODE_NAMES.append((ENGAGEMENT_COLS[i], "E_" + ENGAGEMENT[i]))  

# ---------- dectect grid boxes ----------
def cell_box(page, row, col, margin=CELL_MARGIN):
    """Turn a row and column number into the cell's pixel box.

    page: one page dict from prepare_pages (has the lines measured on that scan)

    Row r is between page["row_lines"][r] and page["row_lines"][r + 1];
    column c is between page["col_lines"][c] and page["col_lines"][c + 1].
    Each side is moved `margin` pixels inward to stay off the grid lines.

    Returns (x0, y0, x1, y1): top-left corner and bottom-right corner.
    """
    # top-left
    x0 = page["col_lines"][col] + margin
    y0 = page["row_lines"][row] + margin

    # bottom-right
    x1 = page["col_lines"][col + 1] - margin
    y1 = page["row_lines"][row + 1] - margin

    return x0, y0, x1, y1

def draw_cells(page):
    """Debug picture: a red rectangle inside every checkbox cell.

    page: one page dict from prepare_pages

    Returns a NEW color image - the original table is not changed.
    """
    picture = cv2.cvtColor(page["table"], cv2.COLOR_GRAY2BGR)    # color copy to draw on

    for row in page["interval_rows"]:        # every interval row (header rows skipped)
        for col in CODE_COLS:                # every checkbox column
            x0, y0, x1, y1 = cell_box(page, row, col)
            cv2.rectangle(picture, (x0, y0), (x1, y1), (0, 0, 255), 3)   # red (BGR!), 3 px

    return picture

def ink_fraction(binary, page, row, col):
    """How much of one checkbox is ink, from 0.0 (empty) to 1.0 (all ink).

    binary: the WHOLE table after threshold() - ink = 255, paper = 0.
            (Threshold once per page, then call this for each box.)
    page:   one page dict from prepare_pages
    row:    row number (from page["interval_rows"])
    col:    column number (from CODE_COLS), e.g. 1 = student L

    Empty box -> about 0.00.   Box with an X -> about 0.10-0.25.
    """
    x0, y0, x1, y1 = cell_box(page, row, col)   # where the box is (margin keeps grid lines out)
    cell = binary[y0:y1, x0:x1]                  # cut it out - rows (y) first, then columns (x)
    ink_pixels = np.count_nonzero(cell == 255)
    total_pixels = cell.size

    fraction = ink_pixels / total_pixels

    return fraction

def measure_page(page):
    """Measure the ink in EVERY checkbox on one page.

    table: a prepared (gray, normalized) table from prepare_pages
    page:  1 or 2

    Thresholds the table once, then calls ink_fraction for each box.
    Returns a dict {(row, col): ink fraction}, e.g. {(2, 1): 0.0, (3, 1): 0.123, ...}
    """
    binary = threshold(page["table"])            # ONCE for the whole page

    fractions = {}
    for row in  page["interval_rows"]:    # every interval row (label rows skipped)
        for col in CODE_COLS:            # every checkbox column
            fractions[(row, col)] = ink_fraction(binary, page, row, col)

    return fractions

def read_page(page, labels):
    """Read every checkbox on one page: 1 = checked, 0 = empty.

    page:   one page dict from prepare_pages
    labels: the interval label of each interval row, top to bottom,
            e.g. INTERVALS[80][3] = ["60-62", ..., "78-80"]

    Returns one dict per interval, top to bottom, e.g.
      [{"interval": "60-62", "S_L": 0, "S_Ind": 0, ..., "E_H": 0},
       {"interval": "62-64", "S_L": 1, ...},
       ...]
    Raises ValueError if the page has a different number of interval rows than labels.
    """
    interval_rows = page["interval_rows"]
    if len(labels) != len(interval_rows):
        raise ValueError(f"{page['source']}: {len(interval_rows)} interval rows "
                         f"but {len(labels)} labels")

    fractions = measure_page(page)            # ink in every box: {(row, col): fraction}

    rows = []

    for i in range(len(interval_rows)):
        row      = interval_rows[i]           # row number, e.g. 2
        interval = labels[i]                  # its label,  e.g. "60-62"

        result = {"interval": interval}       # start this interval's dictionary

        for col, name in CODE_NAMES:          # go through all 30 (column, name) pairs
            fraction = fractions[(row, col)]  # how much ink is in this box
            if fraction > CHECK_THRESHOLD:
                result[name] = 1              # checked
            else:
                result[name] = 0              # empty

        rows.append(result)                   # add this interval's finished dictionary

    return rows


def draw_results(page, labels):
    """Debug picture of what read_page decided, to compare with the paper.

    Green box = checked (ink above CHECK_THRESHOLD), red box = empty.
    Every X on the paper should be green; everything else red.

    Returns a NEW color image - the original table is not changed.
    """
    rows = read_page(page, labels)                                # the real results
    picture = cv2.cvtColor(page["table"], cv2.COLOR_GRAY2BGR)     # color copy to draw on

    # Walk read_page's results in the same order it built them:
    # each result dict belongs to one interval row, each name to one column.
    for i in range(len(rows)):
        row    = page["interval_rows"][i]   # row number of this interval, e.g. 2
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
    from layout import INTERVALS

    # One file = one observation: (file name, observation length in min).
    # Add filled scans to FILLED once you have them (Checks 4 and 5 use them).
    BLANKS = [("blank_50.pdf", 50), ("blank_80.pdf", 80), ("blank_110.pdf", 110)]
    FILLED = []                         # e.g. [("obs01.pdf", 80)]

    def load(files):
        """Prepare every page, with its labels: [(page dict, labels), ...]"""
        result = []
        for name, obs_type in files:
            for number, page in enumerate(prepare_pages([name]), start=1):
                result.append((page, INTERVALS[obs_type][number]))
        return result

    def out_name(page, suffix):
        return page["source"].replace(".", "_").replace(" ", "_") + suffix

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blanks = load(BLANKS)
    filled = load(FILLED)

    # ---- Check 1: draw the boxes (look at them to check CELL_MARGIN) ----
    print(f"===== Check 1: box pictures (CELL_MARGIN = {CELL_MARGIN}) =====")
    for page, labels in blanks:
        name = out_name(page, "_cells.png")
        cv2.imwrite(str(OUT_DIR / name), draw_cells(page))
        count = len(page["interval_rows"]) * len(CODE_COLS)
        print(f"{page['source']:18} {page['role']:6} drew {count} boxes -> {name}")

    # ---- Check 2: ink in every box (blank: everything should be empty) ----
    print("\n===== Check 2: ink in every box =====")
    for page, labels in blanks + filled:
        values = [float(v) for v in measure_page(page).values()]

        empty   = [v for v in values if v < 0.01]
        unclear = [v for v in values if 0.01 <= v <= 0.05]
        checked = [v for v in values if v > 0.05]

        print(f"\n{page['source']} ({page['role']}): {len(values)} boxes")
        print(f"  empty   (< 0.01):     {len(empty):4}   biggest: {max(empty, default=0):.3f}")
        print(f"  unclear (0.01-0.05):  {len(unclear):4}   values: {sorted(round(v, 3) for v in unclear)}")
        print(f"  checked (> 0.05):     {len(checked):4}   smallest: {min(checked, default=0):.3f}")

    # ---- Check 3: read_page on the blanks (should find 0 checked boxes) ----
    print("\n===== Check 3: read_page on the blanks =====")
    for page, labels in blanks:
        rows = read_page(page, labels)
        total = sum(value for r in rows for name, value in r.items() if name != "interval")
        print(f"{page['source']:18} {rows[0]['interval']:>6} ... {rows[-1]['interval']:>7}  "
              f"{len(rows)} intervals, {total} checked")

    # ---- Check 4: read the filled pages (1 = checked, 0 = empty) ----
    print("\n===== Check 4: read_page on the filled sheets =====")
    if not filled:
        print("(no filled scans yet - add them to FILLED)")
    for page, labels in filled:
        rows = read_page(page, labels)
        total = sum(value for r in rows for name, value in r.items() if name != "interval")
        print(f"\n{page['source']} ({page['role']}): {len(rows)} intervals, {total} checked boxes")
        for r in rows[:3]:                         # first 3 intervals: only the checked codes
            marked = [name for name, value in r.items() if name != "interval" and value == 1]
            print(f"  {r['interval']:>6}: {marked}")

    # ---- Check 5: result pictures (green = checked, red = empty) ----
    print("\n===== Check 5: result pictures =====")
    if not filled:
        print("(no filled scans yet - add them to FILLED)")
    for page, labels in filled:
        name = out_name(page, "_results.png")
        cv2.imwrite(str(OUT_DIR / name), draw_results(page, labels))
        print(f"{page['source']}: saved {name}")