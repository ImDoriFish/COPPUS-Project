import pytest

from observations import group_observations


def fake(role, name):
    """A fake page dict - grouping only looks at "role" and "source", so no image is needed."""
    return {"source": name, "role": role}


def roles(observations):
    """[(obs_type, pages), ...] -> [(obs_type, ["FIRST", "LAST"]), ...] for easy comparing"""
    return [(obs_type, [p["role"] for p in pages]) for obs_type, pages in observations]


# ---------- correct uploads ----------

@pytest.mark.parametrize("pattern, obs_type", [
    (["FIRST", "LAST"], 50),
    (["FIRST", "MIDDLE", "LAST"], 80),
    (["FIRST", "MIDDLE", "MIDDLE", "LAST"], 110),
])
def test_one_observation(pattern, obs_type):
    pages = [fake(role, f"obs.pdf p{n}") for n, role in enumerate(pattern, start=1)]
    assert roles(group_observations(pages)) == [(obs_type, pattern)]


def test_mixed_lengths_in_one_upload():
    pattern = ["FIRST", "LAST",                         # 50
               "FIRST", "MIDDLE", "MIDDLE", "LAST",     # 110
               "FIRST", "MIDDLE", "LAST"]               # 80
    pages = [fake(role, f"stack.pdf p{n}") for n, role in enumerate(pattern, start=1)]
    assert [obs_type for obs_type, _ in group_observations(pages)] == [50, 110, 80]


def test_pages_stay_in_order():
    pages = [fake("FIRST", "a"), fake("MIDDLE", "b"), fake("LAST", "c")]
    (obs_type, obs_pages), = group_observations(pages)
    assert [p["source"] for p in obs_pages] == ["a", "b", "c"]


def test_empty_upload():
    assert group_observations([]) == []


def test_real_blank_forms(blank_pages):
    observations = group_observations(list(blank_pages.values()))
    assert [obs_type for obs_type, _ in observations] == [50, 80, 110]


# ---------- wrong uploads: each must be an error that names the page ----------

@pytest.mark.parametrize("pattern, message", [
    (["MIDDLE", "LAST"],                     r"^p1: middle page with no first page"),
    (["LAST"],                               r"^p1: last page with no first page"),
    (["FIRST", "MIDDLE"],                    r"^p2: observation starting at p1 has no last page"),
    (["FIRST", "FIRST", "LAST"],             r"^p2: new first page, but the observation before it"),
    (["FIRST", "LAST", "LAST"],              r"^p3: last page with no first page"),
    (["FIRST", "MIDDLE", "MIDDLE", "MIDDLE", "LAST"], r"^p5: .* has 5 pages"),
])
def test_wrong_uploads_raise(pattern, message):
    pages = [fake(role, f"p{n}") for n, role in enumerate(pattern, start=1)]
    with pytest.raises(ValueError, match=message):
        group_observations(pages)
