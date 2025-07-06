let notificationTimeout;

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    const icon = notification.querySelector('.notification-icon');
    const messageSpan = notification.querySelector('.notification-message');

    // Set message and icon based on type
    messageSpan.textContent = message;
    icon.innerHTML = type === 'success' ? '✔️' : type === 'error' ? '❌' : 'ℹ️';

    // Show notification
    notification.classList.remove('hidden');
    clearTimeout(notificationTimeout);

    // Auto-hide after 5 seconds
    notificationTimeout = setTimeout(() => {
        notification.classList.add('hidden');
    }, 5000);
}

function dismissNotification() {
    const notification = document.getElementById('notification');
    notification.classList.add('hidden');
    clearTimeout(notificationTimeout);
}

function snoozeNotification() {
    dismissNotification();
    setTimeout(() => {
        const notification = document.getElementById('notification');
        notification.classList.remove('hidden');
    }, 10000); // Re-show after 10 seconds
}
