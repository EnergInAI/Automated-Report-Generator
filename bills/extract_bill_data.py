import os
import json
import base64
from pathlib import Path
import google.generativeai as genai

# 🔑 Configure Gemini API
genai.configure(api_key="AIzaSyBJJWoTxeWavz7bfLV2s2CkF-jl9bejtF4")

# 📂 Directories
PDF_DIR = Path("bills/pdf")
DATA_DIR = Path("bills/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 🧠 Prompt
PROMPT = """
You are an expert in understanding electricity bills.
Extract the following information and return ONLY valid JSON:

{
  "connection_type": "",
  "sanctioned_load": "",
  "consumer_number": "",
  "consumer_name": "",
  "Phase": "",
  "meter_serial_number": "",
  "division_address": "",
  "last_six_months": [
    {"bill_month": "", "units": "", "Readings": ""}
  ]
}

Rules:
- Return valid JSON only (no markdown or extra text).
- Extract numeric values as numbers, not strings.
- For months, keep format like "MAY-2025".
- Include 'Readings' if visible.
- Use null for missing fields.
"""

# ⚙ Simplified flat-rate bill calculation
def calculate_bill(units: float) -> float:
    """Return estimated bill amount in INR using flat ₹6.8/unit + fixed charge."""
    if units is None:
        return 0.0

    rate_per_unit = 6.8
    fixed_charge = 120  # typical domestic fixed charge
    energy_charge = units * rate_per_unit
    duty = 0.10 * energy_charge  # 10% electricity duty

    total_bill = energy_charge + fixed_charge + duty
    return round(total_bill, 2)


def transform_to_energy_format(data):
    """Convert Gemini-extracted data into the desired 'Energy Consumption' format with computed bills."""
    try:
        transformed = {
            "IVRS_No": data.get("consumer_number"),
            "Consumer_Name": data.get("consumer_name"),
            "Division": data.get("division_address"),
            "Energy_Consumption": {
                "Contract_Demand (kWh)": str(data.get("sanctioned_load", "")).replace("KW", "").strip(),
                "Meter_Type": data.get("Phase", "").split()[0] if data.get("Phase") else None,
                "Monthly_Consumption_and_Bill": []
            }
        }

        for month_data in data.get("last_six_months", []):
            units = month_data.get("units")
            try:
                units_value = float(str(units).replace(",", "").strip())
            except (ValueError, TypeError):
                units_value = None

            bill_amount = calculate_bill(units_value)

            transformed["Energy_Consumption"]["Monthly_Consumption_and_Bill"].append({
                "month": month_data.get("bill_month"),
                "kwh": units_value,
                "bill": bill_amount
            })

        return transformed

    except Exception as e:
        print("[ERROR] Transformation failed:", e)
        return {"error": str(e)}


def extract_bill_data(pdf_path):
    ivrs_no = pdf_path.stem
    print(f"📄 Processing bill: {ivrs_no}")

    try:
        with open(pdf_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode("utf-8")

        contents = [{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": "application/pdf", "data": encoded_file}},
                {"text": PROMPT}
            ]
        }]

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(contents)
        result_text = response.text.strip().replace("json", "").replace("", "").strip()
         # 🧹 Clean unwanted markdown/code fences
        if result_text.startswith("```"):
            # Remove any ```json or ``` marks and ending ```
            result_text = (
                result_text.replace("```json", "")
                .replace("```", "")
                .replace("\n", "")
                .strip()
            )
        try:
            raw_data = json.loads(result_text)
            print("[INFO] JSON parsed successfully.")
        except json.JSONDecodeError:
            print("[WARNING] JSON parsing failed — saving raw text.")
            raw_data = {"error": "Failed to parse JSON", "raw_text": result_text}

        # ✅ Transform and calculate bill
        if "error" not in raw_data:
            data = transform_to_energy_format(raw_data)
        else:
            data = raw_data

        consumer_no = raw_data.get("consumer_number")
        file_name = f"{consumer_no or ivrs_no}_bill_insights.json"
        out_path = DATA_DIR / file_name

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved transformed data → {out_path}")
        return data

    except Exception as e:
        print(f"❌ Error processing {ivrs_no}: {e}")
        return {"error": str(e)}


def process_all_bills():
    print("\n🔍 Scanning all bill PDFs in /pdf...")
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print("⚠ No PDF files found in /pdf.")
        return

    for pdf in pdf_files:
        extract_bill_data(pdf)

    print("\n✅ All bills processed successfully!")


if __name__ == "__main__":
    process_all_bills()
