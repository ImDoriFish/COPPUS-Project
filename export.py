import re
from pathlib import Path

import pandas as pd

from extract import read_page, CODE_NAMES

def observation_rows(observation, name):
    """Read both pages of one observation and join them into 25 rows.

    observation: one pair from group_observations:
                 ((source1, 1, table1), (source2, 2, table2))  - page 1 first
    name:        what to call this observation, e.g. "filled_page_obs1"

    Returns 25 row dicts (15 from page 1 + 10 from page 2), in time order,
    each with two extra keys: "observation" and "source".
    """
    page1, page2 = observation
    source1, _, table1 = page1          # _ = page number, not needed (we know it's 1)
    source2, _, table2 = page2          # (and this one is 2)

    rows = read_page(table1, 1) + read_page(table2, 2)    # 15 + 10 = 25 rows, 0-2 ... 48-50

    for row in rows:
        row["observation"] = name                          # which class
        row["source"] = f"{source1} + {source2}"           # which pages, to find the paper

    return rows


def file_stem(source):
    """The uploaded file's name without extension or page number
    """
    file_name = re.sub(r" p\d+$", "", source)    # drop a trailing " p1", " p2", ...
    return Path(file_name).stem                   # drop ".pdf" / ".png"


def build_table(observations):
    """Read every observation and put all the rows into one table.

    observations: the list from group_observations
    Returns a pandas DataFrame: one row per 2-minute interval (25 per
    observation), columns observation, source, interval, then every code.
    """
    all_rows = []
    count_per_file = {}                  # how many observations each file has had so far

    for observation in observations:
        page1_source = observation[0][0]                      # e.g. "filled_page.pdf p1"
        stem = file_stem(page1_source)                        # e.g. "filled_page"

        count_per_file[stem] = count_per_file.get(stem, 0) + 1
        name = f"{stem}_obs{count_per_file[stem]}"            # e.g. "filled_page_obs1"

        all_rows.extend(observation_rows(observation, name))  # add its 25 rows

    table = pd.DataFrame(all_rows)

    # Put the columns in a sensible order: labels first, then every code
    columns = ["observation", "source", "interval"] + [name for _, name in CODE_NAMES]
    return table[columns]


def save_csv(table, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)

# ---------- Manual check ----------

if __name__ == "__main__":
    from image_prep import prepare_pages
    from observations import group_observations

    pages = prepare_pages(["filled_page.pdf"])
    observations = group_observations(pages)

    rows = observation_rows(observations[0], "filled_page_obs1")

    print(f"{len(rows)} rows")
    print("first:", rows[0]["interval"], "| last:", rows[-1]["interval"])
    print("observation:", rows[0]["observation"])
    print("source:     ", rows[0]["source"])


    table = build_table(observations)

    print(table)
    print(f"\n{table.shape[0]} rows x {table.shape[1]} columns")