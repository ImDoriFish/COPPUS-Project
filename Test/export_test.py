import pandas as pd
import pytest

from export import file_stem, build_table, save_csv
from extract import CODE_NAMES
from observations import group_observations


@pytest.fixture(scope="module")
def table(blank_pages):
    """The CSV table built from the 3 blank forms (50 + 80 + 110 min)."""
    return build_table(group_observations(list(blank_pages.values())))


# ---------- file_stem ----------

@pytest.mark.parametrize("source, stem", [
    ("stack.pdf p3", "stack"),
    ("obs 01.pdf p12", "obs 01"),
    ("page.png", "page"),
])
def test_file_stem(source, stem):
    assert file_stem(source) == stem


# ---------- build_table ----------

def test_rows_per_observation(table):
    # one row per 2 minutes: 50 / 80 / 110 min -> 25 / 40 / 55 rows
    counts = table.groupby("observation").size().to_dict()
    assert counts == {"blank_50_obs1": 25, "blank_80_obs1": 40, "blank_110_obs1": 55}


def test_obs_type_column(table):
    types = table.groupby("observation")["obs_type"].unique().to_dict()
    assert {name: list(t) for name, t in types.items()} == {
        "blank_50_obs1": [50], "blank_80_obs1": [80], "blank_110_obs1": [110]}


def test_column_order(table):
    assert list(table.columns) == (["observation", "obs_type", "source", "interval"]
                                   + [name for _, name in CODE_NAMES])


def test_intervals_in_time_order(table):
    intervals = table[table["observation"] == "blank_110_obs1"]["interval"].tolist()
    assert intervals[0] == "0-2"
    assert intervals[15] == "30-32"           # page 2 starts right after page 1
    assert intervals[-1] == "108-110"


def test_source_lists_every_page(table):
    source = table[table["observation"] == "blank_80_obs1"]["source"].iloc[0]
    assert source == "blank_80.pdf p1 + blank_80.pdf p2 + blank_80.pdf p3"


def test_blanks_have_nothing_checked(table):
    codes = [name for _, name in CODE_NAMES]
    assert table[codes].to_numpy().sum() == 0


# ---------- save_csv ----------

def test_save_csv_round_trip(table, tmp_path):
    path = tmp_path / "new_folder" / "results.csv"          # folder doesn't exist yet
    save_csv(table, path)
    back = pd.read_csv(path)
    assert back.shape == table.shape                         # no extra index column
    assert list(back.columns) == list(table.columns)
