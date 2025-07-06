function editFact(id, category, description) {
    document.getElementById('editFactModal').style.display = 'flex';
    document.getElementById('editFactId').value = id;
    document.getElementById('editCategory').value = category;
    document.getElementById('editDescription').value = description;
}

function closeEditModal() {
    document.getElementById('editFactModal').style.display = 'none';
}

document.getElementById('uploadCsvForm').addEventListener('submit', async function (event) {
    event.preventDefault();
    const formData = new FormData(this);

    try {
        const response = await fetch('/upload-csv', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            alert('CSV uploaded successfully!');
            location.reload(); // Reload the page to reflect new data
        } else {
            const error = await response.json();
            alert(`Error: ${error.message}`);
        }
    } catch (err) {
        console.error('Error uploading CSV:', err);
        alert('An error occurred while uploading the CSV.');
    }
});
