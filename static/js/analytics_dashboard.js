document.addEventListener('DOMContentLoaded', async () => {
    const response = await fetch('/api/analytics');
    const data = await response.json();

    // Facts Chart
    const factsCtx = document.getElementById('factsChart').getContext('2d');
    new Chart(factsCtx, {
        type: 'pie',
        data: {
            labels: ['Verified Facts', 'Unverified Facts'],
            datasets: [{
                data: [data.facts.verified, data.facts.unverified],
                backgroundColor: ['#4caf50', '#f44336']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            }
        }
    });

    // Alerts Chart
    const alertsCtx = document.getElementById('alertsChart').getContext('2d');
    new Chart(alertsCtx, {
        type: 'bar',
        data: {
            labels: ['Resolved Alerts', 'Unresolved Alerts'],
            datasets: [{
                label: 'Alerts',
                data: [data.alerts.resolved, data.alerts.unresolved],
                backgroundColor: ['#2196f3', '#ff9800']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
});
