async function generateReport() {

    const status = document.getElementById("status");

    // Loader
    status.innerHTML = `
    <div class="loader-box">

        <div class="loader"></div>

        <h2 id="stepText">
            Saving User Details...
        </h2>

        <div class="progress">
            <div class="progress-bar" id="bar"></div>
        </div>

    </div>
    `;

    let bar = document.getElementById("bar");
    let stepText = document.getElementById("stepText");

    let progress = 0;

    let interval = setInterval(() => {

        if (progress < 20)
            stepText.innerHTML = "Saving User Details...";
        else if (progress < 40)
            stepText.innerHTML = "Processing Bill Data...";
        else if (progress < 60)
            stepText.innerHTML = "Generating Solar Insights...";
        else if (progress < 80)
            stepText.innerHTML = "Creating Charts...";
        else
            stepText.innerHTML = "Preparing PDF Report...";

        progress++;

        if (progress > 95)
            progress = 95;

        bar.style.width = progress + "%";

    }, 1000);


    // Form Data
    let formData = JSON.parse(localStorage.getItem("formData"));

    let ivrs =
        formData["IVRS Number [Written in Electricity Bill ]"];


    // Bill Data
    let billData = {

        "IVRS_No": ivrs,

        "Consumer_Name": document.getElementById("consumer_name").value,

        "Division": document.getElementById("division").value,

        "Energy_Consumption": {

            "Contract_Demand (kW)": document.getElementById("contract").value,

            "Meter_Type": formData["Meter Type"],

            "Monthly_Consumption_and_Bill": [

                {
                    "month": month1.value,
                    "kwh": Number(kwh1.value),
                    "bill": Number(bill1.value)
                },

                {
                    "month": month2.value,
                    "kwh": Number(kwh2.value),
                    "bill": Number(bill2.value)
                },

                {
                    "month": month3.value,
                    "kwh": Number(kwh3.value),
                    "bill": Number(bill3.value)
                },

                {
                    "month": month4.value,
                    "kwh": Number(kwh4.value),
                    "bill": Number(bill4.value)
                },

                {
                    "month": month5.value,
                    "kwh": Number(kwh5.value),
                    "bill": Number(bill5.value)
                },

                {
                    "month": month6.value,
                    "kwh": Number(kwh6.value),
                    "bill": Number(bill6.value)
                }

            ]
        }
    };


    let payload = {

        ...formData,

        bill_data: billData

    };


    try {

        let response = await fetch(
            "http://127.0.0.1:8000/generate-report",
            {

                method: "POST",

                headers: {

                    "Content-Type": "application/json"

                },

                body: JSON.stringify(payload)

            }

        );


        if (!response.ok)
            throw new Error("Report generation failed");


        clearInterval(interval);

        bar.style.width = "100%";

        // SUCCESS MESSAGE + BUTTON
        status.innerHTML = `

        <div class="success-box">

            <h2 style="color:green">
                ✅ Report Generated Successfully
            </h2>

            <br>

            <button id="downloadBtn">

                Download PDF

            </button>

        </div>

        `;


        document.getElementById("downloadBtn").onclick = () => {

            window.open(
                `http://127.0.0.1:8000/download-report/${ivrs}`,
                "_blank"
            );

        };


        localStorage.removeItem("formData");

    }

    catch (error) {

        clearInterval(interval);

        status.innerHTML = `

        <h2 style="color:red">

            Error Generating Report

        </h2>

        <p>

            ${error}

        </p>

        `;

        console.error(error);

    }

}