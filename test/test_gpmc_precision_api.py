"""GPMC working precision and projective distance are separate options."""
import pytest
from QuPRS import check_equivalence


@pytest.mark.parametrize("invalid", [0, 15, 60, 91, True, "90", 30.0, None])
def test_invalid_precision_rejected_before_loading_circuits(invalid):
    with pytest.raises(ValueError, match="gpmc_precision_digits"):
        check_equivalence(
            "not a circuit", "not a circuit", gpmc_precision_digits=invalid,
        )


def test_high_precision_is_gpmc_only():
    with pytest.raises(ValueError, match="only applies to GPMC"):
        check_equivalence(
            "not a circuit", "not a circuit", tool_name="ganak",
            gpmc_precision_digits=90,
        )
