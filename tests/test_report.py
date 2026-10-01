import pytest

from mini_report.mini_report import co2_text
from solar_calc import compute_solar_insights

MONTHS = [
    {"kwh": 148, "bill": 1628}, {"kwh": 90, "bill": 990}, {"kwh": 52, "bill": 572},
    {"kwh": 40, "bill": 440}, {"kwh": 42, "bill": 462}, {"kwh": 187, "bill": 2057},
]


def solar(months, meter="Single-phase", area_m2=46.45):
    data = {
        "Energy Consumption": {"Meter Type": meter, "Monthly Consumption & Bill": months},
        "Solar Feasibility": {"Calculated Installation Area (m²)": str(area_m2)},
    }
    out = compute_solar_insights(data)["solar_insights"]
    return next(v for k, v in out.items() if "kW" in k)


def test_known_values_unchanged():
    s = solar(MONTHS)
    assert s["system_size_kw"] == 5
    assert s["annual_generation_kwh"] == 7735
    assert s["annual_saving_inr"] == 12298
    assert s["finance"]["gross_capex_inr"] == 300000
    assert s["finance"]["subsidy_inr"] == 78000
    assert s["finance"]["ten_year_emi_inr"] == 2711


def test_payback_is_none_when_bill_below_interest():
    # Low bills: EMI (= avg bill) can't cover the loan interest -> template shows a fallback
    assert solar(MONTHS)["finance"]["estimated_loan_duration_years"] is None


def test_payback_exists_for_high_bills():
    high = [{"kwh": 900, "bill": 9000}] * 6
    assert solar(high, area_m2=200)["finance"]["estimated_loan_duration_years"]


@pytest.mark.parametrize("tons,expected", [
    (0, "0 kg"), (0.36, "360 kg"), (1, "1 ton"), (1.4, "1.4 tons"), (25, "25 tons"),
])
def test_co2_text(tons, expected):
    assert co2_text(tons) == expected
