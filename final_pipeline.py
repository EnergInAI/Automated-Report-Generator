# ================================
# final_pipeline.py
# ================================
import os
import json
from datetime import datetime
from solar_calc import compute_solar_insights   # ← imported solar logic
import sys
IVRS_NUMBER=sys.argv[1]

#IVRS_NUMBER = "N2253012669"  # change IVRS here

BASE_DIR = os.path.dirname(__file__)
FORM_DIR = os.path.join(BASE_DIR, "form", "data")
BILL_DIR = os.path.join(BASE_DIR, "bills", "data")
RESULT_DIR = os.path.join(BASE_DIR, "result", "final_insights")


# -------------------------------
# Utility
# -------------------------------
def load_json_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] {path}: {e}")
        return {}


def save_json(data, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[✓] Saved: {path}")
    except Exception as e:
        print(f"[ERROR] Could not save {path}: {e}")


# -------------------------------
# Merge Form + Bill
# -------------------------------
def merge_form_and_bill(form_data, bill_data):
    ivrs = str(bill_data.get("IVRS_No") or form_data.get("IVRS Number [Written in Electricity Bill ]", IVRS_NUMBER))
    owner_name = form_data.get("Name of House Owner", "Unknown")
    owner_contact = str(form_data.get("Phone Number", ""))
    address = form_data.get("Full Address (including PIN Code)", "N/A")

    energy_data = bill_data.get("Energy_Consumption", {})
    meter_type = form_data.get("Meter Type") or energy_data.get("Meter_Type")

    shadow_area_ft = form_data.get("Shadow Free Roof Area for Solar Panel  (in sq. ft.)", 0)
    roof_area_m2 = round(float(shadow_area_ft) * 0.092903, 2) if shadow_area_ft else 0

    return {
        "id": owner_contact,
        "timestamp": datetime.now().isoformat(),
        "Basic Information": {
            "IVRS Number": ivrs,
            "Owner Name": owner_name,
            "Owner Contact": owner_contact,
            "Owner Address": address,
            "Climate Zone": form_data.get("Climate Zone")
        },
        "Energy Consumption": {
            "Contract Demand (kWh)": energy_data.get("Contract_Demand (kWh)", "N/A"),
            "Meter Type": meter_type,
            "Monthly Consumption & Bill": energy_data.get("Monthly_Consumption_and_Bill", [])
        },
        "Solar Feasibility": {
            "Existing Solar System": "No",
            "Available Roof Area (m²)": str(roof_area_m2),
            "Shadowed Area (m²)": "0",
            "No Shadow Area (m²)": str(roof_area_m2),
            "Calculated Installation Area (m²)": str(roof_area_m2),
            "Electric Panel Capacity (kW)": energy_data.get("Contract_Demand (kWh)", "N/A")
        }
    }


# -------------------------------
# Main pipeline
# -------------------------------
def run_final_pipeline():
    print(f"[*] Generating final insights for IVRS {IVRS_NUMBER}")

    form_path = os.path.join(FORM_DIR, f"{IVRS_NUMBER}_form_insights.json")
    bill_path = os.path.join(BILL_DIR, f"{IVRS_NUMBER}_bill_insights.json")
    form_data = load_json_safe(form_path)
    bill_data = load_json_safe(bill_path)
    if not form_data or not bill_data:
        print("[!] Missing form or bill data.")
        return

    final_data = merge_form_and_bill(form_data, bill_data)

    # --- Solar ---
    solar_data = compute_solar_insights(final_data)
    final_data["Solar Insights"] = solar_data["solar_insights"]

    out_path = os.path.join(RESULT_DIR, f"{IVRS_NUMBER}_final_insights.json")
    save_json(final_data, out_path)
    print(f"[✓] Final insights saved → {out_path}")


if __name__ == "__main__":
    run_final_pipeline()