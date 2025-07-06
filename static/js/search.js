document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.querySelector('#search-form'); // Use the correct form ID
    const resultsSection = document.querySelector('.results-section');

    searchForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const category = document.getElementById('category').value.trim().toLowerCase();
        const keywords = document.getElementById('keywords').value.trim();

        if (!category && !keywords) {
            alert('Please enter a category or keywords to search.');
            return;
        }

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category, keywords: keywords.split(',').map(kw => kw.trim()) })
            });

            if (response.ok) {
                const facts = await response.json();
                console.log("🔹 Facts Received:", facts); // Debugging: Log the response
                displayResults(facts);
            } else {
                resultsSection.innerHTML = '<p>No facts found matching the criteria.</p>';
            }
        } catch (error) {
            console.error('Error fetching search results:', error);
            resultsSection.innerHTML = '<p>An error occurred while searching. Please try again later.</p>';
        }
    });

    function displayResults(facts) {
        if (facts.length === 0) {
            resultsSection.innerHTML = '<p>No matching facts were found. Please refine your search criteria.</p>';
            return;
        }

        const resultsList = document.createElement('ul');
        resultsList.innerHTML = facts.map(fact => `
            <li>
                <strong>Category:</strong> ${fact.category}<br>
                <strong>Headline:</strong> ${fact.headline}
            </li>
        `).join('');
        resultsSection.innerHTML = '';
        resultsSection.appendChild(resultsList);
    }
});
