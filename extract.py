import cv2

from layout import (ROW_LINES, COL_LINES, INTERVAL_ROWS,
                    STUDENT_COLS, INSTRUCTOR_COLS, ENGAGEMENT_COLS)

# All columns that hold checkboxes, left to right
CODE_COLS = STUDENT_COLS + INSTRUCTOR_COLS + ENGAGEMENT_COLS

# How many pixels to shrink each cell on every side, so the box stays
# inside the cell and doesn't include the grid lines.
CELL_MARGIN = 4

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
    y1 = ROW_LINES[page][col + 1] - margin

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


# ---------- Manual check ----------

if __name__ == "__main__":
    from image_prep import prepare_pages, OUT_DIR

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for source, page, table in prepare_pages(["blank_01.pdf", "blank_02.pdf"]):
        picture = draw_cells(table, page)
        out_path = OUT_DIR / f"page{page}_cells.png"
        cv2.imwrite(str(out_path), picture)

        count = len(INTERVAL_ROWS[page]) * len(CODE_COLS)
        print(f"{source} -> page {page}: drew {count} boxes -> {out_path.name}")