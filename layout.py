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


