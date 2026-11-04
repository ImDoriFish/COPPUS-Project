"""Tool: score the vision model on the tally-mark quiz.

Run:   python score_quiz.py                 (uses VLM_MODEL from vlm.py)
       python score_quiz.py qwen3-vl:8b     (try another model)

Reads out/quiz/quiz.csv (your answer key from make_quiz.py), asks the model
about every crop, and prints how many it got right plus every mistake.
Also saves out/quiz/results_<model>.csv to look at later or compare models.
Needs the Ollama app running.
"""

import csv
import sys
import time

import cv2

from image_prep import OUT_DIR
from vlm import VLM_MODEL, check_vlm, count_tallies

QUIZ_DIR = OUT_DIR / "quiz"
QUIZ_CSV = QUIZ_DIR / "quiz.csv"

def load_quiz():
    """The answer key: a list of dicts {"file", "interval", "name", "true_count"}."""
    with open(QUIZ_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row["true_count"] == "":
            raise ValueError(f"{row['file']}: true_count is empty - finish the answer key first")
        row["true_count"] = int(row["true_count"])
    return rows

def score(model):
    """Ask the model about every quiz crop. Returns one result dict per crop."""
    results = []
    for number, row in enumerate(load_quiz(), start=1):
        image = cv2.imread(str(QUIZ_DIR / row["file"]), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"{row['file']} not found in {QUIZ_DIR}")

        start = time.perf_counter()
        count = count_tallies(image, model)               # int, or None = needs review
        seconds = time.perf_counter() - start

        if count is None:
            verdict = "no answer"
        elif count == row["true_count"]:
            verdict = "right"
        else:
            verdict = "wrong"

        results.append({**row, "number": number, "model_count": count,
                        "verdict": verdict, "seconds": round(seconds, 2)})
        print(f"  #{number:<3} {verdict:9}  true {row['true_count']}  model {count}")
    return results


def report(model, results):
    """Print the summary and save the results CSV."""
    total = len(results)
    right = [r for r in results if r["verdict"] == "right"]
    wrong = [r for r in results if r["verdict"] == "wrong"]
    blank = [r for r in results if r["verdict"] == "no answer"]
    seconds = sum(r["seconds"] for r in results)

    print(f"\nModel: {model}     {total} crops")
    print(f"Right:     {len(right):3} / {total}   ({len(right) / total:.0%})")
    print(f"Wrong:     {len(wrong):3}")
    print(f"No answer: {len(blank):3}   (reply wasn't a clean number -> needs review)")
    print(f"Time:      {seconds / total:.1f} s per crop ({seconds:.0f} s total)")

    if wrong or blank:
        print("\nMistakes:")
        for r in wrong + blank:
            print(f"  #{r['number']:<3} {r['file']:42}  true {r['true_count']}  model {r['model_count']}")

    out = QUIZ_DIR / f"results_{model.replace(':', '_')}.csv"
    columns = ["number", "file", "interval", "name", "true_count", "model_count", "verdict", "seconds"]
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in results:
            writer.writerow({c: r[c] for c in columns})
    print(f"\nSaved {out}")


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else VLM_MODEL
    check_vlm(model)
    print(f"Asking {model} about every quiz crop...")
    results = score(model)
    report(model, results)


if __name__ == "__main__":
    main()