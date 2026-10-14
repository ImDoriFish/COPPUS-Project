from layout import PAGE_SIZES

# How far a table's shape may be from a page's expected shape and still
# count as that page (0.15 = 15%). Further off than this -> error.
RATIO_TOLERANCE = 0.15


def identify_page(table):
    h, w = table.shape           
    ratio = w / h #calcuating the actual width/height ratio of the loaded pic

    best_page = None
    best_diff = None

    for page, (page_w, page_h) in PAGE_SIZES.items():
        expected = page_w / page_h
        diff = abs(ratio - expected) / expected    # calculate the different between the template ratio vs the acutal loaded pic ratio

        if best_diff is None or diff < best_diff:
            best_page = page
            best_diff = diff

    if best_diff > RATIO_TOLERANCE:
        raise ValueError(
            f"Table shape {ratio:.2f} (width/height) matches neither page 1 nor page 2")

    return best_page

# ---------- Manual check ----------

if __name__ == "__main__":
    # Imported here (not at the top) so image_prep.py can import this file
    # later without the two files importing each other in a circle.
    from image_prep import prepare_pages

    for source, page, table in prepare_pages(["blank_01.pdf", "blank_02.pdf"]):
        h, w = table.shape
        print(f"{source}: {w} x {h}, ratio {w / h:.2f} -> page {identify_page(table)}")