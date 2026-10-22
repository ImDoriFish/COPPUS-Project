"""COPUS form layout (new 2026-10 forms: 50 / 80 / 110 min): the MEANINGS only.

No functions, no logic - just what the printed form means: code names,
which column holds which code, and the interval label of every row.

WHERE the lines are is NOT stored here: grid.py measures the row and column
lines on every scan (the forms aren't all drawn at the same proportions).
"""

# ---------- Column codes (left to right, as printed) ----------

STUDENT    = ["L", "Ind", "Fol", "CG", "WG", "C", "OG", "AnQ", "SQ", "WC",
              "Prd", "SP", "T/Q", "W", "O"]                                                 # 15 (new: C)
INSTRUCTOR = ["Lec", "RtW", "FUp", "PQ", "CQ", "AnQ", "MG", "1o1", "D/V", "Adm", "W", "O"]  # 12
ENGAGEMENT = ["L", "M", "H"]                                                                # 3
INTER      = ["InterI", "InterT"]          # tally marks - read in Milestone B              # 2


# ---------- Which column holds which codes (same on every page) ----------
#
# Column c = between the c-th and (c+1)-th vertical line found on the scan.
#   column 0      = "min" (time labels)   - skipped
#   columns 1-15  = STUDENT
#   columns 16-27 = INSTRUCTOR
#   columns 28-30 = ENGAGEMENT (L, M, H)
#   columns 31-32 = INTER (InterI, InterT) - Milestone B
#   column 33     = Comments               - Milestone C
STUDENT_COLS    = list(range(1, 16))     # [1, ..., 15]
INSTRUCTOR_COLS = list(range(16, 28))    # [16, ..., 27]
ENGAGEMENT_COLS = list(range(28, 31))    # [28, 29, 30]
INTER_COLS      = list(range(31, 33))    # [31, 32]

# Every page has this many vertical lines (34 columns) - used to check a scan
COL_LINE_COUNT = 35

# How many interval rows each kind of page has
ROLE_INTERVALS = {"FIRST": 15, "MIDDLE": 15, "LAST": 10}


# ---------- Observation types ----------

# Number of pages in an observation -> its length in minutes
OBS_TYPES = {2: 50, 3: 80, 4: 110}


# ---------- Row labels: INTERVALS[obs_type][page_number] ----------
#
# One label per interval row, top to bottom, e.g. INTERVALS[80][3] = "60-62" ... "78-80".
# FIRST / MIDDLE pages have 15 interval rows, the LAST page has 10.

INTERVALS = {
    50: {
        1: [f"{m}-{m + 2}" for m in range(0, 30, 2)],     # "0-2"   ... "28-30"   (15)
        2: [f"{m}-{m + 2}" for m in range(30, 50, 2)],    # "30-32" ... "48-50"   (10)
    },
    80: {
        1: [f"{m}-{m + 2}" for m in range(0, 30, 2)],     # "0-2"   ... "28-30"   (15)
        2: [f"{m}-{m + 2}" for m in range(30, 60, 2)],    # "30-32" ... "58-60"   (15)
        3: [f"{m}-{m + 2}" for m in range(60, 80, 2)],    # "60-62" ... "78-80"   (10)
    },
    110: {
        1: [f"{m}-{m + 2}" for m in range(0, 30, 2)],     # "0-2"   ... "28-30"   (15)
        2: [f"{m}-{m + 2}" for m in range(30, 60, 2)],    # "30-32" ... "58-60"   (15)
        3: [f"{m}-{m + 2}" for m in range(60, 90, 2)],    # "60-62" ... "88-90"   (15)
        4: [f"{m}-{m + 2}" for m in range(90, 110, 2)],   # "90-92" ... "108-110" (10)
    },
}