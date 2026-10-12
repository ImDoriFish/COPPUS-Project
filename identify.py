from layout import PAGE_SIZES

# How far a table's shape may be from a page's expected shape and still
# count as that page (0.15 = 15%). Further off than this -> error.
RATIO_TOLERANCE = 0.15


def identify_page(table):
    h, w = table.shape           
    ratio = w / h

    best_page = None
    best_diff = None

    for page, (page_w, page_h) in PAGE_SIZES.items():
        expected = page_w / page_h
        diff = abs(ratio - expected) / expected    # 0.05 = 5% off

        if best_diff is None or diff < best_diff:
            best_page = page
            best_diff = diff

    if best_diff > RATIO_TOLERANCE:
        raise ValueError(
            f"Table shape {ratio:.2f} (width/height) matches neither page 1 nor page 2")

    return best_page