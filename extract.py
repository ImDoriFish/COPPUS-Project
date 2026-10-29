import cv2
import numpy as np
from layout import (STUDENT, INSTRUCTOR, ENGAGEMENT, INTER,
                    STUDENT_COLS, INSTRUCTOR_COLS, ENGAGEMENT_COLS, INTER_COLS)
from image_prep import OUT_DIR

# Threshold of how much ink inside of a check box
CHECK_THRESHOLD = 0.03

# A pixel counts as ink if it's at least this much darker than the paper (0-255 gray levels).
# Not Otsu: on scans with very dark grid lines, Otsu's cut-off drops light pencil marks.
INK_DROP = 30

# All columns that hold checkboxes, left to right
CODE_COLS = STUDENT_COLS + INSTRUCTOR_COLS + ENGAGEMENT_COLS

# How many pixels to shrink each cell on every side, so the box stays
# inside the cell and doesn't include the grid lines.
CELL_MARGIN = 8

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

def ink_mask(table):
    """Black-and-white version of the table for reading boxes: ink = 255, paper = 0.

    A pixel is ink if it's at least INK_DROP darker than the paper. The paper
    colour is the table's median gray (most of the table is white paper), so it
    adapts to each scan.
    """
    paper = np.median(table)

    cutoff = paper - INK_DROP
    dark_pixels = table < cutoff
    mask = dark_pixels * 255
    mask = mask.astype(np.uint8)

    return mask

def measure_page(page):
    """Measure the ink in EVERY checkbox on one page.
    page:  

    Thresholds the table once, then calls ink_fraction for each box.
    Returns a dict {(row, col): ink fraction}, e.g. {(2, 1): 0.0, (3, 1): 0.123, ...}
    """
    binary = ink_mask(page["table"])            # ONCE for the whole page

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


# ---------- Crops for the model (InterI / InterT, later Comments / Summary) ----------
#
# Cut cells out of the GRAY table and enlarge them, so vlm.py can send them to
# the vision model. Uses the same cell_box (and CELL_MARGIN) as the checkboxes.

# Enlarge every crop this many times - cells are only ~60 x 95 px at 300 dpi,
# and vision models do better on bigger images.
CROP_SCALE = 4

# Where save_crops writes the crops (only for looking at them)
CROPS_DIR = OUT_DIR / "crops"

# Tally-mark columns: (column number, CSV name), like CODE_NAMES
INTER_NAMES = []
for i in range(len(INTER)):
    INTER_NAMES.append((INTER_COLS[i], "E_" + INTER[i]))      # → (31, "E_InterI")


def crop_cell(page, row, col):
    """Cut one cell out of the table and enlarge it, ready to send to the model.

    page: one page dict from prepare_pages
    row:  row number (from page["interval_rows"])
    col:  column number, e.g. 31 = InterI

    Returns a NEW gray image, CROP_SCALE times bigger than the cell
    (CELL_MARGIN cut off each side, so the grid lines stay out).
    """
    x0, y0, x1, y1 = cell_box(page, row, col)          # where the cell is (same as for checkboxes)
    cell = page["table"][y0:y1, x0:x1]                 # cut it from the GRAY table: real pen strokes
    return cv2.resize(cell, None, fx=CROP_SCALE, fy=CROP_SCALE, interpolation=cv2.INTER_CUBIC)   # enlarge


def inter_crops(page, labels):
    """Crop the InterI and InterT cell of every interval row on one page.

    page:   one page dict from prepare_pages
    labels: the interval label of each interval row, top to bottom
            (same as read_page), e.g. INTERVALS[80][3] = ["60-62", ..., "78-80"]

    Returns one dict per crop, in order (2 per interval row), e.g.
      [{"interval": "60-62", "name": "E_InterI", "image": <crop>},
       {"interval": "60-62", "name": "E_InterT", "image": <crop>},
       {"interval": "62-64", "name": "E_InterI", "image": <crop>}, ...]
    Raises ValueError if the page has a different number of interval rows than labels.
    """
    interval_rows = page["interval_rows"]
    if len(labels) != len(interval_rows):
        raise ValueError(f"{page['source']}: {len(interval_rows)} interval rows "
                         f"but {len(labels)} labels")

    crops = []
    for i in range(len(interval_rows)):
        row = interval_rows[i]                       # row number, e.g. 2
        for col, name in INTER_NAMES:                # (31, "E_InterI"), (32, "E_InterT")
            crops.append({
                "interval": labels[i],               # which row of the CSV, e.g. "60-62"
                "name": name,                        # which column of the CSV
                "image": crop_cell(page, row, col),  # the enlarged cell
            })
    return crops


#debug
def save_crops(crops, source, out_dir=OUT_DIR / "crops"):
    """Save crops as PNG files, to look at them (not needed by the pipeline).

    crops:   the list from inter_crops (each has "interval", "name", "image")
    source:  the page's source label, e.g. "obs01.pdf p2" - goes into the file name
    out_dir: folder to save in (created if needed)

    File names say where each crop came from, e.g.
        out/crops/obs01_pdf_p2_30-32_E_InterI.png
    Returns the list of saved paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = source.replace(".", "_").replace(" ", "_")     # "obs01.pdf p2" -> "obs01_pdf_p2"

    paths = []
    for crop in crops:
        path = out_dir / f"{stem}_{crop['interval']}_{crop['name']}.png"
        cv2.imwrite(str(path), crop["image"])
        paths.append(path)
    return paths


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

    # ---- Check 6: crops for the model (InterI / InterT) ----
    print("\n===== Check 6: InterI / InterT crops -> out/crops/ =====")
    for page, labels in blanks + filled:
        crops = inter_crops(page, labels)
        paths = save_crops(crops, page["source"])
        darkest = max(int((crop["image"] < 128).sum()) for crop in crops)   # dark pixels in any crop
        print(f"{page['source']:18} saved {len(paths)} crops, e.g. {paths[0].name}  "
              f"(most dark pixels in one crop: {darkest})")