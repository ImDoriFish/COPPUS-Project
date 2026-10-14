"""COPUS form layout: everything we know about the printed form, as data.

No functions, no logic - other files import this when they need to know
something about the form (sizes, code names, interval labels, and later
the cell positions).
"""

# ---------- Table sizes ----------

# Size every warped table gets resized to, as (width, height) in pixels.
# Measured from the blank forms (blank_01.pdf, blank_02.pdf) at 300 dpi.
PAGE_SIZES = {
    1: (2737, 1392),   # page 1: 0-30 min,  15 interval rows
    2: (2736, 909),    # page 2: 30-50 min, 10 interval rows
}


# ---------- Column codes (left to right, as printed) ----------

STUDENT    = ["L", "Ind", "Fol", "CG", "WG", "OG", "AnQ", "SQ", "WC", "Prd", "SP", "T/Q", "W", "O"]   # 14
INSTRUCTOR = ["Lec", "RtW", "FUp", "PQ", "CQ", "AnQ", "MG", "1o1", "D/V", "Adm", "W", "O"]          # 12
ENGAGEMENT = ["L", "M", "H"]                                                                        # 3




# ---------- Row labels: the 2-minute intervals on each page ----------

INTERVALS = {
    1: [f"{m}-{m + 2}" for m in range(0, 30, 2)],    # "0-2"   ... "28-30"  (15)
    2: [f"{m}-{m + 2}" for m in range(30, 50, 2)],   # "30-32" ... "48-50"  (10)
}


# ---------- Grid line positions (measured by measure_grid.py) ----------

# y position (pixels from the top) of every horizontal line, per page.
# Measured on the blank tables at exactly PAGE_SIZES - if PAGE_SIZES
# changes, run measure_grid.py again and replace these.
ROW_LINES = {
    1: [8, 38, 74, 157, 240, 322, 404, 486, 520, 599, 683, 765, 848, 930, 972, 1057, 1140, 1222, 1304, 1387],   # 20 lines
    2: [6, 39, 122, 204, 284, 368, 452, 490, 574, 656, 738, 820, 904],                                          # 13 lines
}

# x position (pixels from the left) of every vertical line, per page.
COL_LINES = {
    1: [6, 66, 129, 192, 254, 317, 379, 442, 505, 569, 632, 696, 758, 821, 884, 946, 1008,
        1070, 1134, 1196, 1258, 1322, 1382, 1446, 1508, 1570, 1632, 1696, 1758, 1822, 1884, 1946, 2726],   # 33 lines
    2: [4, 64, 126, 190, 252, 316, 379, 442, 504, 568, 630, 693, 756, 818, 882, 945, 1008,
        1070, 1132, 1195, 1258, 1320, 1382, 1445, 1508, 1570, 1634, 1695, 1758, 1820, 1883, 1946, 2729],   # 33 lines
}


# ---------- What each row and column means ----------
#
# Row r of the table   = between ROW_LINES[page][r] and ROW_LINES[page][r + 1]
# Column c of the table = between COL_LINES[page][c] and COL_LINES[page][c + 1]

# Which rows are 2-minute intervals, in the same order as INTERVALS[page].
# The rows NOT listed are title/label rows (e.g. "L Ind Fol ...") - skipped.
#   page 1: row 0 = title, row 1 = labels, rows 2-6 = 0-2..8-10,
#           row 7 = labels, rows 8-12 = 10-12..18-20,
#           row 13 = labels, rows 14-18 = 20-22..28-30
#   page 2: row 0 = labels, rows 1-5 = 30-32..38-40,
#           row 6 = labels, rows 7-11 = 40-42..48-50
INTERVAL_ROWS = {
    1: [2, 3, 4, 5, 6,   8, 9, 10, 11, 12,   14, 15, 16, 17, 18],
    2: [1, 2, 3, 4, 5,   7, 8, 9, 10, 11],
}

# Which columns hold which codes (the same on both pages), in the same
# order as the STUDENT / INSTRUCTOR / ENGAGEMENT lists above.
#   column 0      = "min" (time labels)        - skipped
#   columns 1-14  = STUDENT codes
#   columns 15-26 = INSTRUCTOR codes
#   columns 27-29 = ENGAGEMENT (L, M, H)
#   column 30     = Inter    (handwriting, Milestone 6)
#   column 31     = Comments (handwriting, Milestone 6)
STUDENT_COLS    = list(range(1, 15))     # [1, 2, ..., 14]
INSTRUCTOR_COLS = list(range(15, 27))    # [15, ..., 26]
ENGAGEMENT_COLS = list(range(27, 30))    # [27, 28, 29]