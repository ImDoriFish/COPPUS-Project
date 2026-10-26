"""Shared test setup: pytest loads this file automatically for every test file in Test/."""

import pytest

from image_prep import prepare_pages


@pytest.fixture(scope="session")
def blank_pages():
    """Every page of the 3 new blank forms, prepared ONCE for all tests.

    {source: page dict}, e.g. blank_pages["blank_80.pdf p3"] -> the 80-min LAST page
    """
    pages = prepare_pages(["blank_50.pdf", "blank_80.pdf", "blank_110.pdf"])
    return {page["source"]: page for page in pages}
