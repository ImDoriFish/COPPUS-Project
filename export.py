import re
from pathlib import Path

import pandas as pd

from extract import read_page, CODE_NAMES
from layout import INTERVALS

def observation_rows(observation, name):
    """Read every page of one observation and join them into one list of rows.

    observation: one (obs_type, pages) tuple from group_observations,
                 e.g. (80, [page_1, page_2, page_3]) - pages in order
    name:        what to call this observation, e.g. "obs01_obs1"

    Returns one row dict per 2-minute interval, in time order
    (25 for 50 min, 40 for 80 min, 55 for 110 min), each with three extra
    keys: "observation", "obs_type" and "source".
    """
    obs_type, pages = observation

    rows = []
    for page_number, page in enumerate(pages, start=1):     # 1, 2, 3, ...
        labels = INTERVALS[obs_type][page_number]           # e.g. INTERVALS[80][3] = "60-62" ... "78-80"
        rows += read_page(page, labels)                     # this page's intervals, in order

    sources = " + ".join(page["source"] for page in pages)  # e.g. "obs01.pdf p1 + obs01.pdf p2 + ..."
    for row in rows:
        row["observation"] = name                           # which class
        row["obs_type"] = obs_type                          # 50 / 80 / 110 min
        row["source"] = sources                             # which pages, to find the paper

    return rows


def file_stem(source):
    """The uploaded file's name without extension or page number
    """
    file_name = re.sub(r" p\d+$", "", source)    # drop a trailing " p1", " p2", ...
    return Path(file_name).stem                   # drop ".pdf" / ".png"


def build_table(observations):
    """Read every observation and put all the rows into one table.

    observations: the list from group_observations, [(obs_type, pages), ...]
    Returns a pandas DataFrame: one row per 2-minute interval,
    columns observation, obs_type, source, interval, then every code.
    """
    all_rows = []
    count_per_file = {}                  # how many observations each file has had so far

    for observation in observations:
        obs_type, pages = observation
        first_source = pages[0]["source"]                     # e.g. "obs01.pdf p1"
        stem = file_stem(first_source)                        # e.g. "obs01"

        count_per_file[stem] = count_per_file.get(stem, 0) + 1
        name = f"{stem}_obs{count_per_file[stem]}"            # e.g. "obs01_obs1"

        all_rows.extend(observation_rows(observation, name))  # add its rows

    table = pd.DataFrame(all_rows)

    # Put the columns in a sensible order: labels first, then every code
    columns = ["observation", "obs_type", "source", "interval"] + [name for _, name in CODE_NAMES]
    return table[columns]


def save_csv(table, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)

if __name__ == "__main__":
    from image_prep import prepare_pages
    from observations import group_observations

    pages = prepare_pages(["blank_50.pdf", "blank_80.pdf", "blank_110.pdf"])
    observations = group_observations(pages)

    # One observation: check the first and last interval
    rows = observation_rows(observations[1], "blank_80_obs1")        # the 80-min form
    print(f"{len(rows)} rows")
    print("first:", rows[0]["interval"], "| last:", rows[-1]["interval"])
    print("observation:", rows[0]["observation"], "| obs_type:", rows[0]["obs_type"])
    print("source:     ", rows[0]["source"])

    # Everything together
    table = build_table(observations)
    print()
    print(table.groupby(["observation", "obs_type"]).size())        # rows per observation
    print(f"\n{table.shape[0]} rows x {table.shape[1]} columns")