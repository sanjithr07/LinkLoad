document.addEventListener('DOMContentLoaded', () => {
    const fetchForm = document.getElementById('url-form');
    const linkInput = document.getElementById('link-input');
    const fetchBtn = document.getElementById('fetch-btn');
    const fetchSpinner = document.getElementById('fetch-spinner');
    const btnText = fetchBtn.querySelector('.btn-text');
    const errorMsg = document.getElementById('error-message');

    const resultView = document.getElementById('result-view');
    const thumbImg = document.getElementById('media-thumb');
    const titleEl = document.getElementById('media-title');
    const durationEl = document.getElementById('media-duration');
    const sourceEl = document.getElementById('media-source');

    const btnVideo = document.getElementById('btn-video');
    const btnAudio = document.getElementById('btn-audio');
    const toggleSlider = document.getElementById('toggle-slider');
    const qualitySelect = document.getElementById('quality-select');

    let currentType = 'video';

    // Toggle handling
    [btnVideo, btnAudio].forEach((btn, index) => {
        btn.addEventListener('click', () => {
            btnVideo.classList.remove('active');
            btnAudio.classList.remove('active');
            btn.classList.add('active');

            // Sliding animation
            toggleSlider.classList.remove('hidden');
            toggleSlider.style.transform = `translateX(${index * 100}%)`;

            currentType = btn.dataset.type;

            // Adjust dropdown text
            if (currentType === 'audio') {
                qualitySelect.options[0].text = "Premium / Max (320kbps)";
                qualitySelect.options[1].text = "High (192kbps)";
                qualitySelect.options[2].text = "Standard (128kbps)";
                qualitySelect.options[3].text = "Basic (64kbps)";
            } else {
                qualitySelect.options[0].text = "Premium / Max";
                qualitySelect.options[1].text = "High (1080p)";
                qualitySelect.options[2].text = "Standard (720p)";
                qualitySelect.options[3].text = "Basic (480p)";
            }
        });
    });

    // Initialize slider position based on active item
    if (btnVideo.classList.contains('active')) {
        toggleSlider.classList.remove('hidden');
        toggleSlider.style.transform = `translateX(0%)`;
    }

    let currentUrl = '';

    fetchForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = linkInput.value.trim();
        if (!url) return;

        currentUrl = url;
        errorMsg.classList.add('hidden');
        errorMsg.textContent = '';
        resultView.classList.add('hidden');
        document.getElementById('download-status').classList.add('hidden');

        fetchBtn.disabled = true;
        fetchSpinner.style.display = 'block';
        btnText.textContent = '';

        try {
            const res = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to fetch info');

            const extractor = data.extractor || 'unknown';
            thumbImg.src = data.thumbnail || 'https://via.placeholder.com/90?text=None';
            titleEl.textContent = data.title;
            sourceEl.textContent = extractor;

            if (data.duration) {
                const mins = Math.floor(data.duration / 60);
                const secs = data.duration % 60;
                durationEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
                durationEl.style.display = 'block';
            } else {
                durationEl.style.display = 'none';
            }

            // Auto Select Option
            const isAudioPlatform = extractor.toLowerCase().includes('soundcloud');
            if (isAudioPlatform) {
                btnAudio.click();
            } else {
                btnVideo.click();
            }

            resultView.classList.remove('hidden');

        } catch (err) {
            errorMsg.textContent = err.message || "An unexpected error occurred.";
            errorMsg.classList.remove('hidden');
        } finally {
            fetchBtn.disabled = false;
            fetchSpinner.style.display = 'none';
            btnText.textContent = 'Proceed';
        }
    });

    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.addEventListener('click', () => {
        const quality = document.getElementById('quality-select').value;
        const params = new URLSearchParams({ url: currentUrl, type: currentType, quality });

        // This triggers a direct direct stream download in the browser natively
        window.location.href = `/api/download?${params.toString()}`;

        const statusEl = document.getElementById('download-status');
        statusEl.classList.remove('hidden');

        // Re-enable
        setTimeout(() => {
            statusEl.classList.add('hidden');
        }, 8000);
    });
});
