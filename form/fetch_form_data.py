import os
import json
import requests
from datetime import datetime

# 🌐 Google Apps Script endpoint that returns your Google Form data as JSON
WEB_APP_URL = "https://script.googleusercontent.com/macros/echo?user_content_key=AehSKLjAoIzQabtqpZSWYIXc6uhcr9NBwkF-S_eDRSrP_h7ZJHPZZFwksDlfIGlv_mxrU6HDmgICIAtmunWEE4w4dpm_n5UFTJ6mz4FTgHnw0wo0o0-8YPYhxRVnKsnuOotyPH-OmzVMv40g4j4Mm1TxP9c_Vj9fhZfvShCUWcIXPOHNzSitR6tJMAr78-wT7CJRTo37jVlqFSsZug6MdD_0G8V_2KWa_qD4MJoxDJVIjnAuP_iQwncJaT6voqVkgxX-Blv-rEoRVLd4B_cyzSfz2l2e-3um5gSA2DSXKMT7ZtaM4He6B_B1t3-ZU8o8OA&lib=M2Xwegal0UvaM8q_tAL6V7cFsysbwZQ-i"

# 🗂️ Local directory and log file
DATA_DIR = "form/data"
LOG_FILE = os.path.join(DATA_DIR, "synced_log.json")


def load_synced_ivrs():
    """Load the list of already-synced IVRS numbers."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            print("⚠️ Corrupted synced_log.json — resetting it.")
            return set()
    return set()

def save_synced_ivrs(ivrs_list):
    """Save the set of synced IVRS numbers."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(ivrs_list)), f, indent=2, ensure_ascii=False)

def fetch_form_data():
    """Fetch all form responses, save new ones by IVRS number, and update sync log."""
    print("🔄 Fetching form data from Google Apps Script...")

    try:
        response = requests.get(WEB_APP_URL)
        response.raise_for_status()
        entries = response.json()

        if not isinstance(entries, list) or not entries:
            print("⚠️ No data received or invalid response format.")
            return []

        # Sort entries (latest first if possible)
        entries.sort(key=lambda x: x.get("Timestamp", ""), reverse=True)

        synced_ivrs = load_synced_ivrs()
        new_ivrs = set()
        saved_files = 0

        for entry in entries:
            ivrs = str(entry.get("IVRS Number [Written in Electricity Bill ]", "")).strip()
            if not ivrs:
                print("⚠️ Skipping entry without IVRS number.")
                continue

            if ivrs in synced_ivrs:
                continue  # already saved before

            file_path = os.path.join(DATA_DIR, f"{ivrs}_form_insights.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)

            print(f"✅ Saved new form → {file_path}")
            new_ivrs.add(ivrs)
            saved_files += 1

        # Update log
        if new_ivrs:
            synced_ivrs.update(new_ivrs)
            save_synced_ivrs(synced_ivrs)

        print(f"\n📦 {saved_files} new record(s) saved. Total synced: {len(synced_ivrs)}.")
        return list(new_ivrs)

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching form data: {e}")
        return []
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON response from Google Apps Script.")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

if __name__ == "__main__":
    fetch_form_data()
