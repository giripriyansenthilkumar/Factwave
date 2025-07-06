document.addEventListener("DOMContentLoaded", function () {
    const themeSelect = document.getElementById("theme");
    const languageSelect = document.getElementById("language");
    const textSizeSelect = document.getElementById("text-size");
    const highContrastToggle = document.getElementById("high-contrast");
    const emailNotifications = document.getElementById("email-notifications");
    const smsNotifications = document.getElementById("sms-notifications");

    // Load saved settings
    themeSelect.value = localStorage.getItem("theme") || "light";
    languageSelect.value = localStorage.getItem("language") || "en";
    textSizeSelect.value = localStorage.getItem("textSize") || "medium";
    highContrastToggle.checked = localStorage.getItem("highContrast") === "true";
    emailNotifications.checked = localStorage.getItem("emailNotifications") === "true";
    smsNotifications.checked = localStorage.getItem("smsNotifications") === "true";

    applyTheme(themeSelect.value);

    themeSelect.addEventListener("change", function () {
        applyTheme(this.value);
        localStorage.setItem("theme", this.value);
    });

    languageSelect.addEventListener("change", function () {
        localStorage.setItem("language", this.value);
    });

    textSizeSelect.addEventListener("change", function () {
        document.body.style.fontSize = this.value === "large" ? "18px" : this.value === "small" ? "12px" : "16px";
        localStorage.setItem("textSize", this.value);
    });

    highContrastToggle.addEventListener("change", function () {
        document.body.style.filter = this.checked ? "contrast(1.5)" : "none";
        localStorage.setItem("highContrast", this.checked);
    });

    emailNotifications.addEventListener("change", function () {
        localStorage.setItem("emailNotifications", this.checked);
    });

    smsNotifications.addEventListener("change", function () {
        localStorage.setItem("smsNotifications", this.checked);
    });

    function applyTheme(theme) {
        document.body.style.background = theme === "dark" ? "#1c1c1c" : "#f4f7fc";
        document.querySelector(".settings-container").style.background = theme === "dark" ? "#333" : "white";
        document.querySelector(".settings-container").style.color = theme === "dark" ? "#fff" : "#333";
    }
});

// Additional functions
function changePassword() {
    alert("Redirecting to Change Password page...");
}

function enable2FA() {
    alert("Two-Factor Authentication Enabled!");
}

function logoutAllDevices() {
    alert("Logged out from all devices.");
}
