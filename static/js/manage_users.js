// JavaScript to handle the modal interactions for adding/removing users
document.addEventListener('DOMContentLoaded', function () {
    const addUserButton = document.querySelector('#add-user');
    const removeUserButton = document.querySelector('#remove-user');
    
    addUserButton.addEventListener('click', function () {
        window.location.href = '/add-user';  // Redirect to the Add User page
    });

    removeUserButton.addEventListener('click', function () {
        window.location.href = '/remove-user';  // Redirect to the Remove User page
    });
});
