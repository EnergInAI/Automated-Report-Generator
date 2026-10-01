import base64
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from solar_calc import compute_solar_insights

CURRENT_DIR = Path(__file__).parent
LOGO_PATH = CURRENT_DIR / "energinai_logo.png"

CURRENT_SCORE = 3
PROJECTED_SCORE = 7
SYSTEM_LIFETIME_YEARS = 25
SQFT_TO_M2 = 0.092903

# ==============================
# Helper Functions
# ==============================
def image_to_base64(path: Path) -> str:
    if not path.exists():
        return ""
    with open(path, "rb") as img_file:
        b64 = base64.b64encode(img_file.read()).decode("utf-8")
    ext = path.suffix.lower().replace('.', '')
    mime = {"jpg": "jpeg"}.get(ext, ext)
    return f"data:image/{mime};base64,{b64}"

def indian_number(n):
    if n is None:
        return ""
    s = str(int(float(n)))
    if len(s) <= 3:
        return s
    out = s[-3:]
    s = s[:-3]
    while len(s) > 0:
        out = s[-2:] + ',' + out
        s = s[:-2]
    return out

def co2_text(tons):
    """Readable CO2 amount: kg below 1 ton, otherwise tons (max 1 decimal)."""
    tons = float(tons or 0)
    if tons < 1:
        return f"{int(round(tons * 1000))} kg"
    if round(tons, 1) == 1:
        return "1 ton"
    value = round(tons, 1)
    return f"{value:g} tons" if value != int(value) else f"{indian_number(value)} tons"

def png_to_base64(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("utf-8")

def score_to_pos(score: float) -> float:
    return (score - 1) / 8 * 100

def get_score_remark(score: float) -> str:
    if score <= 3:
        return "Poor - Inefficient Home with High Energy Wastage"
    elif score <= 5:
        return "Standard - Similar to typical Indian homes"
    elif score <= 7:
        return "Energy Smart - A Well-Optimized Home"
    else:
        return "Highly Efficient - Advanced energy management"

def create_solar_bill_comparison_chart(without_solar, with_solar_cost, Solar_System=None):
    """Return a before/after solar bill chart as PNG bytes."""

    system_kw = None

    # ✅ Safely extract system size even if nested
    if Solar_System:
        if isinstance(Solar_System, dict):
            # direct
            if "system_size_kw" in Solar_System:
                system_kw = Solar_System.get("system_size_kw")
            # nested case (like {"Solar System": {"system_size_kw": 3.2}})
            elif "Solar System" in Solar_System and isinstance(Solar_System["Solar System"], dict):
                system_kw = Solar_System["Solar System"].get("system_size_kw")

    # ✅ Convert numeric-like strings to float
    try:
        if isinstance(system_kw, str):
            system_kw = float(system_kw)
    except ValueError:
        system_kw = None

    # ✅ Build label dynamically
    if system_kw and system_kw > 0:
        labels = ["Without Solar", f"With Solar ({system_kw:.1f} kW)"]
    else:
        labels = ["Without Solar", "With Solar"]

    # ✅ Handle zero or missing values
    # True-to-scale bars: a zero bill is drawn as zero height, never padded up
    values = [max(without_solar, 0), max(with_solar_cost, 0)]
    colors = ["#f28c28", "#228b22"]

    fig, ax = plt.subplots(figsize=(8, 4.3))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Annual Electricity Cost (INR)")
    ax.set_title("Annual Bill Comparison")

    # ✅ Bar labels
    bar_labels = ["₹" + indian_number(v) if v > 0 else "₹0" for v in values]
    ax.bar_label(bars, labels=bar_labels, padding=3)
    ax.set_ylim(0, max(values) * 1.15 if max(values) > 0 else 1)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    return buf.getvalue()


def build_context(ivrs, name, address, meter_type, roof_sqft, monthly):
    """monthly: list of {"month", "kwh", "bill"}. Returns the Jinja context."""
    roof_m2 = round(float(roof_sqft) * SQFT_TO_M2, 2)
    final_data = {
        "Energy Consumption": {
            "Meter Type": meter_type,
            "Monthly Consumption & Bill": monthly,
        },
        "Solar Feasibility": {"Calculated Installation Area (m²)": str(roof_m2)},
    }
    solar_insights = compute_solar_insights(final_data)["solar_insights"]
    solar_data = next((v for k, v in solar_insights.items() if "kW" in k), {})

    billing_data = monthly
    avg_monthly_kwh = sum(float(b["kwh"]) for b in billing_data) / len(billing_data)
    avg_monthly_bill = sum(float(b["bill"]) for b in billing_data) / len(billing_data)

    daily_consumption = round(avg_monthly_kwh / 30, 1)
    projected_year_kwh = avg_monthly_kwh * 12
    projected_yearly_cost = round(avg_monthly_bill * 12, 2)
    yearly_co2_tons = round(projected_year_kwh * 0.82 / 1000, 2)
    average_monthly_bill = round(avg_monthly_bill, 2)

    annual_savings = int(solar_data.get("annual_saving_inr", 0) or 0)
    without_solar_cost = float(solar_data.get("without_solar_cost_inr", 0) or 0)
    with_solar_cost = float(solar_data.get("with_solar_cost_inr", 0) or 0)
    offset_kwh = float(solar_data.get("offset_kwh", 0) or 0)

    # Transformation metrics
    efficiency_saving = projected_year_kwh * 0.07
    avoided_kwh = offset_kwh + efficiency_saving
    co2_prevented_tons = round(avoided_kwh * 0.82 / 1000, 1)

    lifetime_cost_saving = annual_savings * SYSTEM_LIFETIME_YEARS
    lifetime_co2_saved = co2_prevented_tons * SYSTEM_LIFETIME_YEARS

    chart_png = create_solar_bill_comparison_chart(without_solar_cost, with_solar_cost, Solar_System=solar_data)

    context = {
        "form_id": ivrs,
        "datetime_generated": datetime.now().strftime("%B %d, %Y"),
        "homeowner_name": name,
        "homeowner_address": address,
        "logo_base64": image_to_base64(LOGO_PATH),
        "chart_base64": png_to_base64(chart_png),
        "current_score": CURRENT_SCORE,
        "projected_score": PROJECTED_SCORE,
        "current_remark": get_score_remark(CURRENT_SCORE),
        "projected_remark": get_score_remark(PROJECTED_SCORE),
        "current_pos": score_to_pos(CURRENT_SCORE),
        "projected_pos": score_to_pos(PROJECTED_SCORE),
        "average_monthly_bill": average_monthly_bill,
        "projected_yearly_cost": projected_yearly_cost,
        "daily_consumption": daily_consumption,
        "yearly_co2_tons": yearly_co2_tons,
        "annual_savings": annual_savings,
        "co2_prevented_tons": co2_prevented_tons,
        "score_improvement": round(((PROJECTED_SCORE - CURRENT_SCORE) / CURRENT_SCORE) * 100, 1),
        "lifetime_cost_saving": lifetime_cost_saving,
        "lifetime_co2_saved": lifetime_co2_saved,
        "system_lifetime_years": SYSTEM_LIFETIME_YEARS,
        "Solar_Insights": solar_insights,
        "Solar_System": solar_data if "system_size_kw" in solar_data else None,
    }
    return context


def generate_mini_report_pdf(ivrs, name, address, meter_type, roof_sqft, monthly) -> bytes:
    """Build the mini report for one customer and return it as PDF bytes."""
    context = build_context(ivrs, name, address, meter_type, roof_sqft, monthly)

    env = Environment(loader=FileSystemLoader(str(CURRENT_DIR / "templates")))
    env.filters["indian_number"] = indian_number
    env.filters["co2_text"] = co2_text
    html = env.get_template("mini_report.html").render(**context)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 1600})
            page.set_content(html, wait_until="networkidle")
            page.emulate_media(media="print")
            return page.pdf(
                format="A4",
                margin={"top": "15mm", "bottom": "15mm", "left": "10mm", "right": "10mm"},
                print_background=True,
                scale=0.75,
            )
        finally:
            browser.close()
