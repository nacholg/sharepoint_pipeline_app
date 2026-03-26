from voucher_generator.voucher_validator import validate_row


def test_validator_missing_required():
    row = {}

    errors, warnings = validate_row(row)

    assert len(errors) > 0