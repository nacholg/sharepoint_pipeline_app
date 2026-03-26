from pathlib import Path

from voucher_generator.xlsx_to_voucher_json import run_pipeline


def test_pipeline_basic():
    input_file = Path("voucher_generator/LISTADO GENERAL - MODELO.xlsx")

    result = run_pipeline(input_file, sheet_name=None)

    assert len(result["rows"]) > 0
    assert len(result["payloads"]) > 0
    assert len(result["validation"]["rows_with_errors"]) == 0

