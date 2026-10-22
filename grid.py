"""Measure a scanned page's grid live: lines, interval rows, page role."""

import cv2
import numpy as np
from layout import COL_LINE_COUNT, ROLE_INTERVALS

# How long the "stick" is: ink shorter than this (text, specks) gets erased,
# longer straight lines stay. (Need tunning)
STICK_LENGTH = 100

# A row (or column) counts as a line if more than this fraction of it is white.
MIN_FILL = 0.3 

# Rows/columns this close together belong to the same (thick) line.
MERGE_GAP = 3

def find_lines(binary, direction):
    """Return the positions of the grid lines in one direction.

    binary:    thresholded table(wrapped), ink = white (255)
    direction: "horizontal" -> returns y positions (one per horizontal line)
               "vertical"   -> returns x positions (one per vertical line)
    """

    #---------------erase everything that isn't a long straight line---------------------
    if direction == "horizontal":
        stick = cv2.getStructuringElement(cv2.MORPH_RECT, (STICK_LENGTH, 1)) #stick is the structural element (kernel), it defines the shape of the neighborhood pixel like a tempelate shape.
    else:
        stick = cv2.getStructuringElement(cv2.MORPH_RECT, (1, STICK_LENGTH))

    #Modify the threshold image so that the kernel fit on the line (basicly modifying the image so it only contain the grid line (numpy Array))
    only_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, stick)

    #--------------count white pixels in every row (or column)----------------------
    if direction == "horizontal":
        sum_of_white_pixel = only_lines.sum(axis=1) / 255 # calculate the sum of each row
        full_length = binary.shape[1] # Since shape(height, width), and get the table acutal width
    else:
        sum_of_white_pixel = only_lines.sum(axis=0) / 255 # calculate the sum of each column
        full_length = binary.shape[0] # Since shape(height, width), and get the table acutal height

    line_pixels_location = np.where(sum_of_white_pixel > MIN_FILL * full_length)[0] # where return tuple (since only 1 argument pass in).

    # --------------merge neighbours (one thick line -> one position) ----------------

    group_line = [] #a list of list of line 
    for p in line_pixels_location:
        # Check if the list is not empty and if the current line belong in a group by checking the difference 
        #between the current line with the most recent added line in the most added group [-1][-1] means that.
        if group_line and  p - group_line[-1][-1] <= MERGE_GAP:
            group_line[-1].append(p)  # right next to the previous one: same line
        else:
            group_line.append([p])          # a gap: a new line starts

    # Merge all the group together by finding the average per each group and set it as the pixel location for new lines.
    merged_line = []
    for group in group_line:
        average = np.mean(group)
        rounded = round(average)
        position = int(rounded)
        merged_line.append(position)

    return merged_line


# A row is an interval row (has checkboxes) if its height is between these
# multiples of the median row height. Measured on the blanks: interval rows
# ~90-100 px, header rows ~33-50 px (< 0.7x), Summary box ~700 px (> 1.5x).
TALL_MIN = 0.7
TALL_MAX = 1.5

def tall_rows(row_lines):
    """Return the row numbers of the interval rows (the rows with checkboxes).

    row_lines: y positions of the horizontal lines, top to bottom (from find_lines)

    Row r is between row_lines[r] and row_lines[r + 1]. Interval rows are all
    about the same height; header rows are much thinner and the Summary box is
    much taller. The median height is an interval row's height, because most
    rows are interval rows.

    """
    heights = np.diff(row_lines)          # height of every row: line[r+1] - line[r]
    normal = np.median(heights)           # a typical interval row's height

    rows = []
    for row, height in enumerate(heights):
        if TALL_MIN * normal <= height <= TALL_MAX * normal:
            rows.append(row)              # about normal height: an interval row
    return rows

def measure_table(binary):
    """Measure one page's grid: the 3 lists layout.py used to store.

    binary: the warped table after threshold (ink = 255)

    Returns (row_lines, col_lines, interval_rows):
        row_lines      y of every horizontal line, top to bottom
        col_lines      x of every vertical line, left to right
        interval_rows  row numbers of the rows with checkboxes (see tall_rows)
    """
    row_lines = find_lines(binary, "horizontal")
    col_lines = find_lines(binary, "vertical")

    if len(col_lines) != COL_LINE_COUNT:
        raise ValueError(f"found {len(col_lines)} column lines, expected {COL_LINE_COUNT}")

    interval_rows = tall_rows(row_lines)
    return row_lines, col_lines, interval_rows


# The last row is the Summary box (LAST page) if it's this many times taller
# than a normal interval row. Measured: ~7.5x on LAST pages, ~1x on others.
SUMMARY_MIN = 3

# Page 1 (FIRST) has text above the table (Date, Class, code descriptions...).
# Ink fraction above the table: ~0.064 on FIRST pages, ~0.001 on others.
HEADER_MIN_INK = 0.02

# Skip this many pixels right above the table, so the table's own thick top
# border isn't counted as "text above".
HEADER_GAP = 10

def has_summary(row_lines):
    """True if the page ends with the Summary box (a LAST page).

    row_lines: y positions of the horizontal lines, top to bottom

    The Summary box is the last row, and it's much taller than a normal
    interval row (~7.5x on LAST pages, ~1x on the others).
    """
    heights = np.diff(row_lines)          # height of every row
    normal = np.median(heights)           # a typical interval row's height
    return bool(heights[-1] > SUMMARY_MIN * normal)


def has_header(binary, corners):
    """True if there is text above the table (a FIRST page: Date, Class, ...).

    binary:  the thresholded UPRIGHT page (not the warped table), ink = 255
    corners: the table's 4 corners from order_corners
             (top-left, top-right, bottom-right, bottom-left), each (x, y)
    """
    top_left, top_right = corners[0], corners[1]

    top = int(min(top_left[1], top_right[1]))   # y where the table starts
    left = int(top_left[0])                     # only look straight above the table
    right = int(top_right[0])

    area = binary[0 : top - HEADER_GAP, left : right]   # rows first (y), then columns (x)
    if area.size == 0:
        return False                      # table starts at the very top: no room for a header

    ink = np.count_nonzero(area) / area.size
    return bool(ink > HEADER_MIN_INK)

def page_role(row_lines, interval_rows, binary, corners):
    """Decide what kind of page this is: "FIRST", "MIDDLE" or "LAST".

    row_lines:     y positions of the horizontal lines (from measure_table)
    interval_rows: row numbers of the interval rows   (from measure_table)
    binary:        the thresholded UPRIGHT page (for has_header)
    corners:       the table's corners from order_corners (for has_header)
    """
    if has_summary(row_lines):
        role = "LAST"
    elif has_header(binary, corners):
        role = "FIRST"
    else:
        role = "MIDDLE"

    expected = ROLE_INTERVALS[role]
    if len(interval_rows) != expected:
        raise ValueError(f"{role} page: found {len(interval_rows)} interval rows, expected {expected}")

    return role


if __name__ == "__main__":
    # Quick check: measure every page of the new blank forms and print what grid.py finds.
    # Imported here (not at the top) so grid.py itself never depends on image_prep.py:
    # image_prep.py will import grid.py in step 4, and two files importing each other breaks.
    from image_prep import (load_pages, to_gray, rotate_upright, threshold,
                            find_table_corners, order_corners, warp_table)

    for source, img in load_pages(["blank_50.pdf", "blank_80.pdf", "blank_110.pdf"]):
        upright = rotate_upright(to_gray(img))
        page_binary = threshold(upright)                       # whole page (for has_header)
        corners = order_corners(find_table_corners(page_binary))
        table = warp_table(upright, corners)

        row_lines, col_lines, interval_rows = measure_table(threshold(table))
        role = page_role(row_lines, interval_rows, page_binary, corners)

        print(f"{source:18} {role:6}  "
              f"{len(row_lines)} row lines, {len(col_lines)} col lines, "
              f"{len(interval_rows)} interval rows  "
              f"(summary: {has_summary(row_lines)}, header: {has_header(page_binary, corners)})")