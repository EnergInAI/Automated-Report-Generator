const rows = document.getElementById("rows");
const labels = ["Latest month", "1 month before", "2 months before", "3 months before", "4 months before", "5 months before"];
rows.innerHTML = "<table><tr><th></th><th>Units (kWh)</th><th>Bill amount (₹)</th></tr>" + labels.map((l, i) =>
  `<tr><td class="m">${l}</td>
   <td><input type="number" min="0" step="any" inputmode="decimal" id="kwh${i}" placeholder="e.g. 148"></td>
   <td><input type="number" min="0" step="any" inputmode="decimal" id="bill${i}" placeholder="e.g. 1628"></td></tr>`
).join("") + "</table>";

const msg = document.getElementById("msg");
const btn = document.getElementById("btn");

function show(text, kind) {
  msg.textContent = text;
  msg.className = "msg " + kind;
}

document.getElementById("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const v = (id) => document.getElementById(id).value.trim();

  const months = [];
  for (let i = 0; i < labels.length; i++) {
    const kwh = v("kwh" + i), bill = v("bill" + i);
    if (kwh === "" && bill === "") continue;
    if (kwh === "" || bill === "") return show(`${labels[i]}: enter both units and bill amount.`, "err");
    months.push({ kwh: Number(kwh), bill: Number(bill) });
  }
  if (!v("name") || !v("address") || !v("ivrs") || !v("roof")) return show("Please fill in all customer details.", "err");
  if (months.length < 3) return show("Enter at least 3 months of units and bill amounts.", "err");

  btn.disabled = true;
  btn.textContent = "Generating… (can take up to a minute)";
  show("Generating your report, please wait…", "ok");

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: v("name"),
        address: v("address"),
        ivrs: v("ivrs"),
        meter_type: v("meter"),
        roof_area_sqft: Number(v("roof")),
        months,
      }),
    });
    if (res.status === 401) { location.href = "/login"; return; }
    if (!res.ok) {
      let detail = "Something went wrong. Please try again.";
      try {
        const j = await res.json();
        if (typeof j.detail === "string") detail = j.detail;
        else if (Array.isArray(j.detail)) detail = j.detail.map(d => (d.loc || []).slice(1).join(" ") + ": " + d.msg).join("; ");
      } catch (_) {}
      throw new Error(detail);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = v("ivrs").toUpperCase() + "_mini_report.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    show("Report downloaded.", "ok");
  } catch (err) {
    show(err.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate PDF report";
  }
});
