"""The static site builds and shows the same headline numbers as RESULTS.md."""

import html

from causal.report import five_numbers, load
from causal.site import build


def test_site_builds_with_headline_numbers(tmp_path) -> None:
    page = build(tmp_path).read_text()
    for _, value in five_numbers(*load()):
        assert html.escape(value) in page
    assert (tmp_path / "figures" / "synth_paths.png").exists()
