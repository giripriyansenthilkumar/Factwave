document.addEventListener("DOMContentLoaded", function () {
    // Get the form and input elements
    const form = document.getElementById("loginForm");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const usernameError = document.getElementById("usernameError");
    const passwordError = document.getElementById("passwordError");

    // Event listener for form submission
    form.addEventListener("submit", function (event) {
        let valid = true;

        // Reset error messages
        usernameError.textContent = "";
        passwordError.textContent = "";

        // Validate username
        if (usernameInput.value.trim() === "") {
            usernameError.textContent = "Username is required.";
            valid = false;
        }

        // Validate password
        if (passwordInput.value.trim() === "") {
            passwordError.textContent = "Password is required.";
            valid = false;
        }

        // Prevent form submission if validation fails
        if (!valid) {
            event.preventDefault();
        }
    });
});
