"""RESULTS.md numbers must match the JSON they were generated from."""

import re

import pytest

from causal.report import OUT, five_numbers, headline_rows, load


def parse_headline_table(text: str) -> list[dict]:
    section = text.split("## Headline table")[1].split("\n## ")[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] in ("outcome", "---"):
            continue
        keys = ["outcome", "method", "estimate", "ci", "p", "n"]
        rows.append(dict(zip(keys, cells, strict=True)))
    return rows


def close(text: str, value: float, tol: float = 5e-4 + 1e-12) -> bool:
    return abs(float(text) - value) <= tol


def p_matches(text: str, value: float) -> bool:
    return value < 0.001 if text == "<0.001" else close(text, value)


@pytest.fixture(scope="module")
def data():
    twfe, es, synth, power = load()
    return twfe, es, synth, power, OUT.read_text()


def test_headline_table_matches_json(data) -> None:
    twfe, es, synth, power, text = data
    parsed = parse_headline_table(text)
    expected = headline_rows(twfe, es, synth)
    assert len(parsed) == len(expected) > 0
    for got, exp in zip(parsed, expected, strict=True):
        assert got["outcome"] == exp["outcome"] and got["method"] == exp["method"]
        assert close(got["estimate"], exp["estimate"])
        assert p_matches(got["p"], exp["p_value"])
        assert int(got["n"]) == exp["n"]
        if exp["ci_low"] is not None:
            lo, hi = re.findall(r"-?\d+\.\d+", got["ci"])
            assert close(lo, exp["ci_low"]) and close(hi, exp["ci_high"])


def test_five_numbers_present(data) -> None:
    twfe, es, synth, power, text = data
    for key, value in five_numbers(twfe, es, synth, power):
        assert f"**{key}:** {value}" in text


def test_five_numbers_values(data) -> None:
    twfe, es, synth, power, text = data
    att = es["outcomes"]["log_p10_all"]["callaway_santanna"]["overall_att"]["estimate"]
    line = next(v for k, v in five_numbers(twfe, es, synth, power) if k.startswith("10th"))
    assert close(line.split()[0], att)
    mde = power["outcomes"]["log_emp_food"]["mde_80"]
    line = next(v for k, v in five_numbers(twfe, es, synth, power) if k.startswith("Minimum"))
    assert close(line.split()[0], mde)
