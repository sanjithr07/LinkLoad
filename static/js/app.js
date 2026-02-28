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

    // ── Custom dropdown ──────────────────────────────────────────
    const customSelect = document.getElementById('custom-quality-select');
    const csTrigger = document.getElementById('cs-trigger');
    const csValueEl = document.getElementById('cs-value');
    const csOptions = customSelect.querySelectorAll('.cs-option');

    const optionSets = {
        video: [
            { value: 'very_high', name: 'Premium / Max', desc: 'Best available quality', badge: '4K' },
            { value: 'high', name: 'High (1080p)', desc: 'Full HD — recommended', badge: 'HD' },
            { value: 'medium', name: 'Standard (720p)', desc: 'Balanced quality & size', badge: 'SD' },
            { value: 'low', name: 'Basic (480p)', desc: 'Smallest file size', badge: 'LQ' },
        ],
        audio: [
            { value: 'very_high', name: 'Premium / Max', desc: '320 kbps — highest quality', badge: 'HI' },
            { value: 'high', name: 'High (192 kbps)', desc: 'Excellent audio fidelity', badge: '192' },
            { value: 'medium', name: 'Standard (128 kbps)', desc: 'Great everyday quality', badge: '128' },
            { value: 'low', name: 'Basic (64 kbps)', desc: 'Smallest file size', badge: '64' },
        ],
    };

    let selectedValue = 'high';

    function updateCustomOptions(type) {
        const set = optionSets[type];
        csOptions.forEach((opt, i) => {
            const data = set[i];
            opt.dataset.value = data.value;
            opt.querySelector('.cs-opt-badge').textContent = data.badge;
            opt.querySelector('.cs-opt-name').textContent = data.name;
            opt.querySelector('.cs-opt-desc').textContent = data.desc;
            qualitySelect.options[i].text = data.name;
            qualitySelect.options[i].value = data.value;
        });
        // Re-select whichever index was previously selected
        const idx = [...csOptions].findIndex(o => o.dataset.value === selectedValue);
        selectOption(csOptions[idx >= 0 ? idx : 1], false);
    }

    function selectOption(optEl, closeDrawer = true) {
        csOptions.forEach(o => o.classList.remove('selected'));
        optEl.classList.add('selected');
        selectedValue = optEl.dataset.value;
        qualitySelect.value = selectedValue;
        csValueEl.textContent = optEl.querySelector('.cs-opt-name').textContent;
        if (closeDrawer) customSelect.classList.remove('open');
    }

    csTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        customSelect.classList.toggle('open');
    });

    csOptions.forEach(opt => {
        opt.addEventListener('click', () => selectOption(opt));
    });

    document.addEventListener('click', (e) => {
        if (!customSelect.contains(e.target)) customSelect.classList.remove('open');
    });

    // ── Video / Audio toggle ─────────────────────────────────────
    [btnVideo, btnAudio].forEach((btn, index) => {
        btn.addEventListener('click', () => {
            btnVideo.classList.remove('active');
            btnAudio.classList.remove('active');
            btn.classList.add('active');

            toggleSlider.classList.remove('hidden');
            toggleSlider.style.transform = `translateX(${index * 100}%)`;

            currentType = btn.dataset.type;
            updateCustomOptions(currentType);
        });
    });

    // Initialise slider
    if (btnVideo.classList.contains('active')) {
        toggleSlider.classList.remove('hidden');
        toggleSlider.style.transform = 'translateX(0%)';
    }

    let currentUrl = '';

    // ── Fetch media info ─────────────────────────────────────────
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
                body: JSON.stringify({ url }),
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

            const isAudioPlatform = extractor.toLowerCase().includes('soundcloud');
            (isAudioPlatform ? btnAudio : btnVideo).click();

            resultView.classList.remove('hidden');

        } catch (err) {
            errorMsg.textContent = err.message || 'An unexpected error occurred.';
            errorMsg.classList.remove('hidden');
        } finally {
            fetchBtn.disabled = false;
            fetchSpinner.style.display = 'none';
            btnText.textContent = 'Proceed';
        }
    });

    // ── Download ─────────────────────────────────────────────────
    document.getElementById('download-btn').addEventListener('click', () => {
        const params = new URLSearchParams({ url: currentUrl, type: currentType, quality: selectedValue });
        window.location.href = `/api/download?${params.toString()}`;

        const statusEl = document.getElementById('download-status');
        statusEl.classList.remove('hidden');
        setTimeout(() => statusEl.classList.add('hidden'), 8000);
    });
});
