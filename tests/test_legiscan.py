import json
from pathlib import Path

from juniper.fetch.legiscan import parse_search_results

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_search_results_skips_summary():
    raw = json.loads((FIXTURES / "legiscan_search_tx.json").read_text())
    bills = parse_search_results(raw)
    assert len(bills) == 2
    assert {b.bill_number for b in bills} == {"HB1234", "SB45"}


def test_parse_search_results_extracts_fields():
    raw = json.loads((FIXTURES / "legiscan_search_tx.json").read_text())
    bills = {b.bill_id: b for b in parse_search_results(raw)}
    hb1234 = bills[1234567]
    assert hb1234.state == "TX"
    assert hb1234.change_hash == "aaaa1111"
    assert hb1234.title == "Relating to data center electricity procurement."
