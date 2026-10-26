"""
One observation = one FIRST page, then any MIDDLE pages, then one LAST page:
  50 min  = FIRST LAST
  80 min  = FIRST MIDDLE LAST
  110 min = FIRST MIDDLE MIDDLE LAST
Pages come in upload order. Each observation's pages must be together and
in order. Anything else (a page outside an observation, a missing FIRST or
LAST page, an unknown length) is an error naming the page.
"""

from layout import OBS_TYPES


def group_observations(pages):
    """Group the pages into observations: FIRST, MIDDLE..., LAST.

    pages: the list from prepare_pages, in upload order - one dict per page,
           e.g. {"source": "obs01.pdf p1", "role": "FIRST", "table": ..., ...}

    Returns a list of observations, each a tuple (obs_type, pages):
        obs_type  50 / 80 / 110 (from the number of pages, see layout.OBS_TYPES)
        pages     that observation's page dicts, in order (page 1 first)
    e.g. [(80, [page_A, page_B, page_C]), (50, [page_D, page_E])]

    Raises ValueError naming the page if the pages don't fit together.
    """
    observations = []
    current = None              # pages of the observation being collected (None = none open)

    for page in pages:
        role = page["role"]
        source = page["source"]

        if role == "FIRST":
            if current is not None:
                raise ValueError(f"{source}: new first page, but the observation before it "
                                 f"(starting at {current[0]['source']}) has no last page")
            current = [page]                        # start a new observation

        elif role == "MIDDLE":
            if current is None:
                raise ValueError(f"{source}: middle page with no first page before it")
            current.append(page)

        else:  # "LAST"
            if current is None:
                raise ValueError(f"{source}: last page with no first page before it")
            current.append(page)

            count = len(current)
            if count not in OBS_TYPES:
                raise ValueError(f"{source}: observation starting at {current[0]['source']} "
                                 f"has {count} pages - no COPUS form has that many")

            observations.append((OBS_TYPES[count], current))   # finished
            current = None                                      # nothing open now

    if current is not None:
        raise ValueError(f"{current[-1]['source']}: observation starting at "
                         f"{current[0]['source']} has no last page")

    return observations


# ---------- Manual check ----------

if __name__ == "__main__":
    from image_prep import prepare_pages

    pages = prepare_pages(["blank_50.pdf", "blank_80.pdf", "blank_110.pdf"])
    observations = group_observations(pages)

    print(f"{len(pages)} pages -> {len(observations)} observation(s)")
    for n, (obs_type, obs_pages) in enumerate(observations, start=1):
        sources = ", ".join(page["source"] for page in obs_pages)
        print(f"  observation {n}: {obs_type} min - {sources}")

    # Wrong uploads: each one should give a clear error
    print("\nWrong uploads:")
    first, middle, last = pages[2], pages[3], pages[4]      # blank_80 p1, p2, p3
    wrong = {
        "missing first page":   [middle, last],
        "missing last page":    [first, middle],
        "last page twice":      [first, last, last],
        "first page twice":     [first, first, last],
        "too many middles":     [first, middle, middle, middle, last],
    }
    for name, test_pages in wrong.items():
        try:
            group_observations(test_pages)
            print(f"  {name}: NO ERROR (bug!)")
        except ValueError as e:
            print(f"  {name}: {e}")