import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
import matplotlib.pyplot as plt

# ==============================
# Path Setup
# ==============================
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent
FINAL_INSIGHTS_DIR = PROJECT_ROOT / "result" / "final_insights"
FINAL_REPORTS_DIR = PROJECT_ROOT / "reports"
FINAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# CONFIGURATION
# ==============================
import sys
FORM_ID = sys.argv[1]# change form ID here27338211
CURRENT_SCORE = 3
PROJECTED_SCORE = 7
SYSTEM_LIFETIME_YEARS = 25

FINAL_INSIGHTS = FINAL_INSIGHTS_DIR / f"{FORM_ID}_final_insights.json"
if not FINAL_INSIGHTS.exists():
    raise FileNotFoundError(f"Final insights not found: {FINAL_INSIGHTS}")

LOGO_PATH = CURRENT_DIR / "energinai_logo.png"
if not FINAL_INSIGHTS.exists():
    raise FileNotFoundError(f"Final insights not found: {FINAL_INSIGHTS}")
if not LOGO_PATH.exists():
    raise FileNotFoundError(f"Logo file not found at: {LOGO_PATH}")

# ==============================
# Helper Functions
# ==============================
def image_to_base64(path: Path) -> str:
    if not path.exists():
        return ""
    with open(path, "rb") as img_file:
        b64 = base64.b64encode(img_file.read()).decode("utf-8")
    ext = path.suffix.lower().replace('.', '')
    return f"data:image/{ext};base64,{b64}"

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

def create_solar_bill_comparison_chart(without_solar, with_solar_cost, form_id, Solar_System=None):
    """Generate a before/after solar bill chart (auto-includes system size from insights)."""
    import matplotlib.pyplot as plt
    from pathlib import Path

    min_display_value = 100
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
    without_val = without_solar if without_solar > 0 else min_display_value
    with_val = with_solar_cost if with_solar_cost > 0 else min_display_value
    values = [without_val, with_val]
    colors = ["#f28c28", "#228b22"]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Annual Electricity Cost (INR)")
    ax.set_title("Annual Bill Comparison")

    # ✅ Bar labels
    bar_labels = []
    for original_val, display_val in zip([without_solar, with_solar_cost], values):
        if display_val == min_display_value:
            bar_labels.append("₹0 (est.)")
        else:
            bar_labels.append("₹" + indian_number(original_val))
    ax.bar_label(bars, labels=bar_labels, padding=3)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    charts_dir = CURRENT_DIR / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_path = charts_dir / f"solar_bill_comparison_{form_id}.png"

    plt.tight_layout()
    plt.savefig(chart_path, dpi=200)
    plt.close(fig)
    return chart_path


# ==============================
# Load Data
# ==============================
with open(FINAL_INSIGHTS, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Generating Mini Report for IVRS: {FORM_ID}")

# ==============================
# Extract Metrics
# ==============================
basic_info = data.get("Basic Information", {})
energy_data = data.get("Energy Consumption", {})

# 🔍 Auto-detect solar data key dynamically (e.g. "3.0kW", "5kW", etc.)
solar_insights = data.get("Solar Insights", {})
solar_data = next((v for k, v in solar_insights.items() if "kW" in k), {})

homeowner_name = basic_info.get("Owner Name", "N/A")
homeowner_address = basic_info.get("Owner Address", "N/A")

billing_data = energy_data.get("Monthly Consumption & Bill", [])
if not billing_data:
    raise ValueError("No billing history found in final insights JSON")

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

# ==============================
# Transformation & Environmental Metrics
# ==============================
baseline_kwh = projected_year_kwh
efficiency_saving = baseline_kwh * 0.07
avoided_kwh = offset_kwh + efficiency_saving
co2_prevented_tons = round(avoided_kwh * 0.82 / 1000, 1)

lifetime_cost_saving = annual_savings * SYSTEM_LIFETIME_YEARS
lifetime_co2_saved = co2_prevented_tons * SYSTEM_LIFETIME_YEARS

trees = int(co2_prevented_tons * 45)
garden_area = int(trees * 400)
km_driving = int(co2_prevented_tons * 2400)
rural_homes = projected_year_kwh / 1200

environmental_impacts = {
    "trees": trees if trees >= 5 else None,
    "garden_area": indian_number(garden_area) if garden_area >= 2000 else None,
    "km_driving": indian_number(km_driving) if km_driving >= 100 else None,
    "rural_homes": round(rural_homes, 1) if rural_homes >= 2 else None,
}

# ==============================
# Chart Generation
# ==============================
solar_insights = data.get("Solar Insights", {})
solar_data = next((v for k, v in solar_insights.items() if "kW" in k), {})
size = basic_info.get("Owner Name", "N/A")
chart_path = create_solar_bill_comparison_chart(without_solar_cost, with_solar_cost, FORM_ID, Solar_System=solar_data)

# ==============================
# Scoring & Context
# ==============================
current_remark = get_score_remark(CURRENT_SCORE)
projected_remark = get_score_remark(PROJECTED_SCORE)
score_improvement = round(((PROJECTED_SCORE - CURRENT_SCORE) / CURRENT_SCORE) * 100, 1)

context = {
    "form_id": FORM_ID,
    "datetime_generated": datetime.now().strftime("%B %d, %Y"),
    "homeowner_name": homeowner_name,
    "homeowner_address": homeowner_address,
    "logo_base64": image_to_base64(LOGO_PATH),
    "chart_base64": image_to_base64(chart_path),
    "current_score": CURRENT_SCORE,
    "projected_score": PROJECTED_SCORE,
    "current_remark": current_remark,
    "projected_remark": projected_remark,
    "current_pos": score_to_pos(CURRENT_SCORE),
    "projected_pos": score_to_pos(PROJECTED_SCORE),
    "average_monthly_bill": average_monthly_bill,
    "projected_yearly_cost": projected_yearly_cost,
    "daily_consumption": daily_consumption,
    "yearly_co2_tons": yearly_co2_tons,
    "annual_savings": annual_savings,
    "co2_prevented_tons": co2_prevented_tons,
    "score_improvement": score_improvement,
    "lifetime_cost_saving": lifetime_cost_saving,
    "lifetime_co2_saved": lifetime_co2_saved,
    "system_lifetime_years": SYSTEM_LIFETIME_YEARS,
    
}
context.update({k: v for k, v in environmental_impacts.items() if v})

# ==============================
# Add Solar Feasibility & Solar Insights to Context
# ==============================

solar_insights = data.get("Solar Insights", {})

# Find the first valid solar system entry (e.g. "3.2kW")
solar_system_data = None
for key, val in solar_insights.items():
    if isinstance(val, dict) and "system_size_kw" in val:
        solar_system_data = val
        break

# Add them to context for Jinja template access
context["Solar_Insights"] = solar_insights
context["Solar_System"] = solar_system_data


# ==============================
# Render HTML
# ==============================
env = Environment(loader=FileSystemLoader(str(CURRENT_DIR / "templates")))
env.filters["indian_number"] = indian_number
template = env.get_template("mini_report.html")
output_html = template.render(**context)

html_path = FINAL_REPORTS_DIR / f"{FORM_ID}_mini_report.html"
html_path.write_text(output_html, encoding="utf-8")

print(f"HTML ready: {html_path.name}")

# ==============================
# Generate PDF
# ==============================
async def generate_pdf_playwright(html_content, pdf_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({'width': 1200, 'height': 1600})
        await page.set_content(html_content, wait_until='networkidle')
        await page.emulate_media(media='print')
        await page.pdf(
            path=pdf_path,
            format='A4',
            margin={'top': '15mm', 'bottom': '15mm', 'left': '10mm', 'right': '10mm'},
            print_background=True,
            scale=0.75,
        )
        await browser.close()

pdf_path = FINAL_REPORTS_DIR / f"{FORM_ID}_mini_report.pdf"
asyncio.run(generate_pdf_playwright(output_html, str(pdf_path)))

print(f"PDF generated: {pdf_path.name}")
