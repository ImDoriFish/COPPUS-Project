"""Tool: build the tally-mark quiz (Milestone B5) from a filled scan.

Run:   python make_quiz.py Filled_sheet.pdf
       (any number of files; default Filled_sheet.pdf)

Saves the InterI / InterT crops that have strokes (plus a few empty ones) to
out/quiz/, and writes out/quiz/quiz.csv with a true_count column for you to fill.
The crops are exactly what the model gets: inter_crops' cleaned black-on-white.

If an old answer key exists (out/quiz_old.csv), answers are copied over by
file name, so you only fill in cells that are new.

out/ is gitignored, so these crops (real data) never go to GitHub.
"""

import csv
import random
import sys

import cv2
import numpy as np

from image_prep import prepare_pages, OUT_DIR
from observations import group_observations
from extract import inter_crops
from layout import INTERVALS

QUIZ_DIR = OUT_DIR / "quiz"
QUIZ_CSV = QUIZ_DIR / "quiz.csv"
OLD_KEY = OUT_DIR / "quiz_old.csv"       # a previous answer key to copy answers from

# A crop counts as "has strokes" if more than this fraction of it is ink AFTER cleaning
MARK_LIMIT = 0.005

# How many EMPTY cells to add, so the quiz also checks that the model says 0
EMPTY_COUNT = 10


def quiz_cells(file_names):
    """Every InterI / InterT crop of the scans, cleaned, with how much ink is left.

    Returns a list of dicts: {"file", "interval", "name", "ink", "image"}
    """
    pages = prepare_pages(file_names)
    cells = []
    for obs_type, obs_pages in group_observations(pages):
        for page_number, page in enumerate(obs_pages, start=1):
            stem = page["source"].replace(".", "_").replace(" ", "_")
            for crop in inter_crops(page, INTERVALS[obs_type][page_number]):
                image = crop["image"]                              # black ink (0) on white (255)
                crop["ink"] = np.count_nonzero(image == 0) / image.size
                crop["file"] = f"{stem}_{crop['interval']}_{crop['name']}.png"
                cells.append(crop)
    return cells


def old_answers():
    """{file name: true_count} from a previous answer key, or {} if there is none."""
    if not OLD_KEY.exists():
        return {}
    with open(OLD_KEY, newline="") as f:
        return {row["file"]: row["true_count"] for row in csv.DictReader(f)}


def main():
    file_names = sys.argv[1:] or ["Filled_sheet.pdf"]

    # Never overwrite an answer key you may already have typed into
    if QUIZ_CSV.exists():
        print(f"{QUIZ_CSV} already exists - move it to {OLD_KEY} first "
              f"(its answers will be copied over), then run again")
        return

    cells = quiz_cells(file_names)
    marked = [c for c in cells if c["ink"] > MARK_LIMIT]
    empty = [c for c in cells if c["ink"] <= MARK_LIMIT]

    random.seed(0)                                   # same "random" empties every run
    chosen = marked + random.sample(empty, min(EMPTY_COUNT, len(empty)))

    answers = old_answers()
    copied = 0
    QUIZ_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUIZ_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "interval", "name", "true_count"])
        for c in chosen:
            cv2.imwrite(str(QUIZ_DIR / c["file"]), c["image"])
            answer = answers.get(c["file"], "")      # "" = new cell: you fill it in
            copied += answer != ""
            writer.writerow([c["file"], c["interval"], c["name"], answer])

    print(f"{len(cells)} InterI/InterT cells: {len(marked)} with strokes, {len(empty)} empty")
    print(f"Quiz: {len(chosen)} crops ({len(marked)} with strokes + {len(chosen) - len(marked)} empty)")
    print(f"Answers copied from {OLD_KEY.name}: {copied}  -  still to fill in: {len(chosen) - copied}")
    for c in chosen:
        if c["file"] not in answers:
            print(f"  new: {c['file']}")


if __name__ == "__main__":
    main()