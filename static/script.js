const form = document.getElementById("extractForm");

form.addEventListener("submit", async function(event) {

    event.preventDefault();

    const file = document.getElementById("extractImage").files[0];

    if (!file) {
        return;
    }

    const formData = new FormData();

    formData.append("image", file);

    const result = document.getElementById("result");

    result.innerText = "Extracting message...";

    try {

        const response = await fetch("/extract", {
            method: "POST",
            body: formData
        });

        const message = await response.text();

        result.innerText = message;

    } catch (error) {

        result.innerText = "Something went wrong.";

    }

});