document.addEventListener('DOMContentLoaded', () => {
    const transcriptionOutput = document.getElementById('transcription-output');
    const factCheckOutput = document.getElementById('fact-check-output');

    const eventSource = new EventSource('/live-transcription');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.transcription) {
            transcriptionOutput.textContent = data.transcription;
        }

        if (data.fact_status) {
            factCheckOutput.textContent = `Status: ${data.fact_status.status}, Match Type: ${data.fact_status.match_type}`;
        }

        if (data.error) {
            factCheckOutput.textContent = `Error: ${data.error}`;
        }
    };

    eventSource.onerror = () => {
        factCheckOutput.textContent = 'Connection lost. Please refresh the page.';
        eventSource.close();
    };
});
