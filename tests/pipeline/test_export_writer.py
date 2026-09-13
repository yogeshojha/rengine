from __future__ import annotations

import csv
import json

import pytest

from shared.services.asset_export import columns, writer

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    "raw",
    ["=1+1", "+1", "-1", "@SUM(A1)", "\tvalue", "\rvalue"],
)
def test_a_cell_a_spreadsheet_would_run_is_quoted(raw):
    assert writer.cell(raw).startswith("'")


def test_an_ordinary_cell_is_left_alone():
    assert writer.cell("nmap.org") == "nmap.org"
    assert writer.cell("Go ahead and ScanMe!") == "Go ahead and ScanMe!"


def test_a_title_a_target_wrote_cannot_carry_control_characters():
    assert writer.cell("evil\x00title\x07") == "eviltitle"


def test_a_list_reads_as_one_cell():
    assert writer.cell(["nginx", "php"]) == "nginx; php"


def test_absent_is_empty_never_the_word_none():
    assert writer.cell(None) == ""


def test_a_flag_reads_as_a_word():
    assert writer.cell(True) == "true"
    assert writer.cell(False) == "false"


def test_csv_carries_the_bom_excel_needs(tmp_path):
    path = tmp_path / "rows.csv"

    written = writer.write_csv(path, ["name"], [{"name": "café.example.com"}])

    assert written == 1
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        assert list(csv.reader(handle)) == [["name"], ["café.example.com"]]


def test_a_formula_survives_the_round_trip_as_text(tmp_path):
    path = tmp_path / "rows.csv"

    writer.write_csv(path, ["title"], [{"title": "=cmd|'/c calc'!A1"}])

    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[1] == ["'=cmd|'/c calc'!A1"]


def test_json_holds_the_named_columns_only(tmp_path):
    path = tmp_path / "rows.json"

    written = writer.write_json(
        path, ["name", "status"], [{"name": "a", "status": 200, "secret": "x"}]
    )

    assert written == 1
    assert json.loads(path.read_text()) == [{"name": "a", "status": 200}]


def test_an_empty_json_export_is_still_an_array(tmp_path):
    path = tmp_path / "rows.json"

    assert writer.write_json(path, ["name"], []) == 0
    assert json.loads(path.read_text()) == []


def test_text_writes_one_value_a_line_and_drops_blanks(tmp_path):
    path = tmp_path / "rows.txt"

    written = writer.write_txt(path, iter(["a.example.com", "", "  ", "b.example.com"]))

    assert written == 2
    assert path.read_text() == "a.example.com\nb.example.com\n"


def test_a_negative_number_stays_a_number():
    assert writer.cell(-1) == "-1"
    assert writer.cell(-0.5) == "-0.5"


def test_a_status_code_is_not_quoted():
    assert writer.cell(200) == "200"


def test_evidence_columns_are_absent_until_asked_for():
    plain = columns.headers("vulnerabilities")
    with_evidence = columns.headers("vulnerabilities", evidence=True)

    assert "request" not in plain
    assert "response" not in plain
    assert with_evidence[: len(plain)] == plain
    assert with_evidence[len(plain) :] == ["curl_command", "request", "response"]


def test_only_findings_offer_evidence():
    assert columns.offers_evidence("vulnerabilities") is True
    for dimension in ("web_assets", "endpoints", "services", "ips"):
        assert columns.offers_evidence(dimension) is False
        assert columns.headers(dimension, evidence=True) == columns.headers(dimension)
