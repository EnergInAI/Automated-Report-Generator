function saveForm() {

    let ivrs = document.getElementById("ivrs").value.trim();

    if (ivrs === "") {
        alert("Please enter IVRS Number");
        return;
    }

    let formData = {

        "Timestamp": new Date().toISOString(),

        "Name of House Owner":
            document.getElementById("name").value,

        "Phone Number":
            Number(document.getElementById("phone").value),

        "Full Address (including PIN Code)":
            document.getElementById("address").value,

        "Meter Type":
            document.getElementById("meter").value,

        "IVRS Number [Written in Electricity Bill ]":
            ivrs,

        "Shadow Free Roof Area for Solar Panel  (in sq. ft.)":
            Number(document.getElementById("roof").value)

    };

    // Local Storage me save karo
    localStorage.setItem(
        "formData",
        JSON.stringify(formData)
    );

    // Bill page open karo
    window.location.href = "bill.html";

}