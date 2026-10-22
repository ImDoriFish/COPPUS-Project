from image_prep import prepare_pages, SCANS_DIR, OUT_DIR, IMAGE_EXTS
from observations import group_observations
from export import build_table, save_csv

# The blank forms used to build layout.py - not real observations
TEMPLATES = {"blank_01.pdf", "blank_02.pdf"}

# File types we can read
SCAN_EXTS = {".pdf"} | IMAGE_EXTS          # .pdf, .png, .jpg, .jpeg

OUTPUT_CSV = OUT_DIR / "copus_results.csv"


def find_scans():
    names = []
    for path in sorted(SCANS_DIR.iterdir()):
        if not path.is_file():
            continue                              # skip folders
        if path.suffix.lower() not in SCAN_EXTS:
            continue                              # skip other file types
        if path.name in TEMPLATES:
            continue                              # skip the blank forms
        names.append(path.name)
    return names


def main():
    files = find_scans()
    if not files:
        print(f"No scans found in {SCANS_DIR}")
        return
    print(f"Found {len(files)} file(s): {', '.join(files)}")

    pages = prepare_pages(files)                  # load, straighten, identify page 1/2
    observations = group_observations(pages)      # pair page 1 + page 2
    print(f"{len(pages)} page(s) -> {len(observations)} observation(s)")

    table = build_table(observations)             # read every checkbox, 25 rows each
    save_csv(table, OUTPUT_CSV)
    print(f"Saved {len(table)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()