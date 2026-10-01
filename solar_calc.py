# ================================
# solar_calc.py
# ================================
import math

# -------------------------------
# Configuration & Constants (India)
# -------------------------------

BASE_YIELD_PER_KW = 1547  # kWh generated per kW per year
KW_PER_M2 = 0.17
COST_PER_KW_INR = 60000


# -------------------------------
# Helper Calculations
# -------------------------------

def estimate_capex_subsidy(size_kw: float):
    capex = round(size_kw * COST_PER_KW_INR)
    subsidy = 78000 if size_kw <= 10 else 0
    upfront = 0 if size_kw <= 3 else round(0.1 * capex)
    return capex, subsidy, upfront


def annual_generation_kwh(size_kw):
    return round(size_kw * BASE_YIELD_PER_KW, 1)


def annual_load_kwh(monthly_data):
    if not monthly_data:
        return None
    vals = [float(m.get("kwh", 0)) for m in monthly_data if m.get("kwh") is not None]
    if not vals:
        return None
    avg = sum(vals) / len(vals)
    return round(avg * 12, 1)


def blended_rate_inr(monthly_data):
    if not monthly_data:
        return None
    total_bill = sum(float(m.get("bill", 0)) for m in monthly_data)
    total_kwh = sum(float(m.get("kwh", 0)) for m in monthly_data)
    if total_kwh == 0:
        return None
    return round(total_bill / total_kwh, 2)


# ✅ ✅ ✅ **CORRECT EMI → TENURE FORMULA (NO BINARY SEARCH)**  
def calculate_loan_duration(net_capex, emi, interest_rate):
    if emi <= 0 or net_capex <= 0:
        return None

    r = interest_rate / (12 * 100)  # monthly interest rate

    # EMI must be greater than interest portion
    if emi <= net_capex * r:
        return None

    try:
        num = math.log(emi / (emi - net_capex * r))
        den = math.log(1 + r)
        months = num / den
        return round(months, 1)
    except:
        return None


def calculate_fixed_tenure_emi(net_capex1, interest_rate1, years=10):
    if net_capex1 <= 0:
        return 0

    r = interest_rate1 / (12 * 100)
    n = years * 12

    if r == 0:
        return net_capex1 / n

    emi2 = (net_capex1 * r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return int(emi2)


# -------------------------------
# Main Recommendation Function
# -------------------------------

def recommend_solar_system(final_data):
    energy = final_data.get("Energy Consumption", {})
    solar_info = final_data.get("Solar Feasibility", {})
    monthly = energy.get("Monthly Consumption & Bill", [])
    usable_area = float(solar_info.get("Calculated Installation Area (m²)", 0))
    meter_type = (energy.get("Meter Type") or "").upper()

    annual_load = annual_load_kwh(monthly)
    rate = blended_rate_inr(monthly)
    if annual_load is None or rate is None:
        return {"summary": "Insufficient data to compute recommendation."}

    base_cost = round(annual_load * rate, 0)
    max_kw = 6 if "SINGLE" in meter_type else 50

    ideal_kw = annual_load / BASE_YIELD_PER_KW
    ideal_kw = max(ideal_kw, 5.0)
    ideal_kw = min(ideal_kw, max_kw)

    if 3 <= ideal_kw <= 3.5:
        final_kw = 3
    elif 3.5 < ideal_kw <= 6:
        final_kw = 5
    elif 6 < ideal_kw <= 8:
        final_kw = 8
    elif 8 < ideal_kw <= 10:
        final_kw = 10
    else:
        final_kw = round(min(ideal_kw, max_kw), 1)
    

    area_needed = final_kw / KW_PER_M2
    fits = area_needed <= usable_area
    if not fits:
        final_kw = max(round(usable_area * KW_PER_M2, 1), 3.0)

    gen = annual_generation_kwh(final_kw)
    offset_kwh = gen

    if offset_kwh < 0.95 * annual_load:
        while offset_kwh < 0.95 * annual_load and final_kw < max_kw:
            final_kw += 0.1
            gen = annual_generation_kwh(final_kw)
            offset_kwh = gen

    offset_pct = round(min(100, max(95, offset_kwh / annual_load * 100)), 1)
    annual_saving = round(min(offset_kwh, annual_load) * rate, 0)
    monthly_saving = round(annual_saving / 12, 0)

    capex, subsidy, upfront = estimate_capex_subsidy(final_kw)
    net_capex = capex - subsidy

    interest_rate = 7.0 if net_capex <= 200000 else 8.15

    avg_monthly_bill = round(sum(float(m.get("bill", 0)) for m in monthly) / len(monthly), 0) if monthly else 0
    monthly_emi = avg_monthly_bill if avg_monthly_bill > 0 else 0

    months_to_repay = calculate_loan_duration(net_capex, monthly_emi, interest_rate)
    years_to_repay = round(months_to_repay / 12, 1) if months_to_repay else None

    yearly_emi = monthly_emi * 12
    net_benefit = annual_saving - yearly_emi

    
    ten_year_emi = calculate_fixed_tenure_emi(net_capex, interest_rate, years=10)

    return {
        f"{round(final_kw,1)}kW": {
            "system_size_kw": round(final_kw, 1),
            "fits": fits,
            "area_needed_m2": round(final_kw / KW_PER_M2, 1),
            "usable_area_m2": round(usable_area, 1),
            "annual_generation_kwh": round(gen, 1),
            "annual_load_kwh": annual_load,
            "offset_kwh": round(min(gen, annual_load), 1),
            "offset_percent": offset_pct,
            "without_solar_cost_inr": base_cost,
            "with_solar_cost_inr": None if gen >= annual_load else round(base_cost - annual_saving, 0),
            "annual_saving_inr": annual_saving,
            "finance": {
                "gross_capex_inr": capex,
                "subsidy_inr": subsidy,
                "upfront_inr": upfront,
                "net_capex_inr": net_capex,
                "interest_rate_percent": interest_rate,
                "approx_monthly_bill_inr": avg_monthly_bill,
                "monthly_payment_inr": monthly_emi,
                "yearly_payment_inr": yearly_emi,
                "estimated_loan_duration_months": months_to_repay,
                "estimated_loan_duration_years": years_to_repay,
                "net_benefit_first_year_inr": net_benefit,
                "ten_year_emi_inr": ten_year_emi,
                "explanation": (
                    f"Interest rate = {interest_rate}%. "
                    "Loan duration auto-calculated so EMI ≈ user's average bill."
                )
            }
        },
        "summary": (
            f"{round(final_kw,1)} kW system offsets {offset_pct}% of your load, "
            f"saving ~₹{annual_saving}/yr. EMI ≈ ₹{monthly_emi}/month at {interest_rate}% for about {years_to_repay} years."
        )
    }


# -------------------------------
# Wrapper for pipeline use
# -------------------------------

def compute_solar_insights(final_data):
    return {"solar_insights": recommend_solar_system(final_data)}
