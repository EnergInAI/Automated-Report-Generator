from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import subprocess
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FORM_DIR = os.path.join(BASE_DIR, "form", "data")
BILL_DIR = os.path.join(BASE_DIR, "bills", "data")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(FORM_DIR, exist_ok=True)
os.makedirs(BILL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


@app.get("/")
def home():
    return {
        "message": "API Running Successfully"
    }


@app.post("/generate-report")
def generate_report(data: dict):

    try:

        ivrs = data["IVRS Number [Written in Electricity Bill ]"]

        # ====================================
        # FORM JSON
        # ====================================

        form_json = {
            "Timestamp": data["Timestamp"],
            "Name of House Owner": data["Name of House Owner"],
            "Phone Number": data["Phone Number"],
            "Full Address (including PIN Code)": data["Full Address (including PIN Code)"],
            "Meter Type": data["Meter Type"],
            "IVRS Number [Written in Electricity Bill ]": ivrs,
            "Shadow Free Roof Area for Solar Panel  (in sq. ft.)":
                data["Shadow Free Roof Area for Solar Panel  (in sq. ft.)"]
        }

        form_path = os.path.join(
            FORM_DIR,
            f"{ivrs}_form_insights.json"
        )

        with open(form_path, "w", encoding="utf-8") as f:
            json.dump(form_json, f, indent=4)

        print("Form JSON saved")


        # ====================================
        # BILL JSON
        # ====================================

        bill_path = os.path.join(
            BILL_DIR,
            f"{ivrs}_bill_insights.json"
        )

        with open(bill_path, "w", encoding="utf-8") as f:
            json.dump(data["bill_data"], f, indent=4)

        print("Bill JSON saved")


        # ====================================
        # RUN final_pipeline.py
        # ====================================

        subprocess.run(
            ["python", "final_pipeline.py", ivrs],
            cwd=BASE_DIR,
            check=True
        )


        # ====================================
        # RUN mini_report.py
        # ====================================

        subprocess.run(
            ["python", "mini_report/mini_report.py", ivrs],
            cwd=BASE_DIR,
            check=True
        )

        print("Mini Report Completed")


        # ====================================
        # PDF PATH
        # ====================================

        pdf_path = os.path.join(
            REPORT_DIR,
            f"{ivrs}_mini_report.pdf"
        )

        # PDF generate hone ka wait
        timeout = 40        # maximum 40 sec wait
        elapsed = 0

        while elapsed < timeout:

            if os.path.exists(pdf_path):

                # file size >0 bhi check kar lo
                if os.path.getsize(pdf_path) > 0:
                    break

            time.sleep(1)
            elapsed += 1

        # agar fir bhi file nahi mili
        if not os.path.exists(pdf_path):

            return JSONResponse(
                status_code=404,
                content={
                    "message": "PDF not found"
                }
            )

        print("PDF Found :", pdf_path)

        return {
            "status": "success",
            "ivrs": ivrs
        }

    except subprocess.CalledProcessError as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": f"Pipeline Error : {str(e)}"
            }
        )

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e)
            }
        )
@app.get("/download-report/{ivrs}")
def download_report(ivrs: str):

    pdf_path = os.path.join(
        REPORT_DIR,
        f"{ivrs}_mini_report.pdf"
    )

    if not os.path.exists(pdf_path):

        return JSONResponse(
            status_code=404,
            content={
                "status": "waiting"
            }
        )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{ivrs}_mini_report.pdf"
    )