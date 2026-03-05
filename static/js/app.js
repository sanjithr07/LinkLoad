// LinkLoad Application Logic
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elements = {
        formContainer: document.getElementById('form-container'),
        form: document.getElementById('url-form'),
        input: document.getElementById('link-input'),
        fetchBtn: document.getElementById('fetch-btn'),
        fetchBtnText: document.querySelector('#fetch-btn .btn-text'),
        fetchSpinner: document.getElementById('fetch-spinner'),
        errorMsg: document.getElementById('error-message'),

        resultView: document.getElementById('result-view'),
        mediaThumb: document.getElementById('media-thumb'),
        mediaTitle: document.getElementById('media-title'),
        mediaDuration: document.getElementById('media-duration'),
        mediaSource: document.getElementById('media-source'),

        optionsView: document.getElementById('options-view'),
        segmentBtns: document.querySelectorAll('.segment-btn'),
        segmentBg: document.getElementById('segment-active-bg'),

        dropdown: document.getElementById('quality-dropdown'),
        dropdownTrigger: document.querySelector('.dropdown-trigger'),
        dropdownValueText: document.getElementById('dropdown-value-text'),
        dropdownMenu: document.getElementById('dropdown-menu'),

        downloadBtn: document.getElementById('download-btn'),

        postDownloadView: document.getElementById('post-download-view'),
        statusTitle: document.getElementById('status-title'),
        resetBtn: document.getElementById('reset-btn')
    };

    // State
    const state = {
        currentUrl: '',
        type: 'video', // 'video' | 'audio'
        quality: 'high'
    };

    // Quality Configuration
    const qualityOptions = {
        video: [
            { value: 'very_high', name: 'Premium (Max)', desc: 'Highest available quality', badge: '4K' },
            { value: 'high', name: 'High (1080p)', desc: 'Standard Full HD', badge: 'HD' },
            { value: 'medium', name: 'Medium (720p)', desc: 'Good balance of quality/size', badge: 'SD' },
            { value: 'low', name: 'Low (480p)', desc: 'Smaller file size', badge: 'LQ' }
        ],
        audio: [
            { value: 'very_high', name: 'Lossless / Max', desc: 'Highest bitrate available', badge: '320k' },
            { value: 'high', name: 'High (192kbps)', desc: 'Great audio quality', badge: '192k' },
            { value: 'medium', name: 'Standard (128kbps)', desc: 'Good for most uses', badge: '128k' },
            { value: 'low', name: 'Basic (64kbps)', desc: 'Smallest audio size', badge: '64k' }
        ]
    };

    // Initialize Dropdown Options
    function renderDropdownOptions() {
        const options = qualityOptions[state.type];
        elements.dropdownMenu.innerHTML = options.map(opt => `
            <div class="dropdown-item ${opt.value === state.quality ? 'selected' : ''}" data-value="${opt.value}">
                <div class="item-info">
                    <span class="item-name">${opt.name}</span>
                    <span class="item-desc">${opt.desc}</span>
                </div>
                <div class="item-badge">${opt.badge}</div>
            </div>
        `).join('');

        // Attach listeners to new items
        document.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                state.quality = item.dataset.value;
                elements.dropdownValueText.textContent = item.querySelector('.item-name').textContent;
                renderDropdownOptions(); // Re-render to update 'selected' class
                elements.dropdown.classList.remove('open');
            });
        });

        // Ensure the current selected text matches default/fallback
        const selectedOpt = options.find(o => o.value === state.quality) || options[1];
        state.quality = selectedOpt.value;
        elements.dropdownValueText.textContent = selectedOpt.name;
    }

    // Toggle Dropdown
    elements.dropdownTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        elements.dropdown.classList.toggle('open');
    });

    // Close Dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!elements.dropdown.contains(e.target)) {
            elements.dropdown.classList.remove('open');
        }
    });

    // Segmented Controller (Video/Audio Toggle)
    elements.segmentBtns.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            // Update UI 
            elements.segmentBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            elements.segmentBg.style.transform = `translateX(${index * 100}%)`;

            // Update State
            state.type = btn.dataset.type;
            renderDropdownOptions();
        });
    });

    // Step 1 -> Step 2: Fetch Media Information
    elements.form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = elements.input.value.trim();
        if (!url) return;

        state.currentUrl = url;

        // Reset Error state
        elements.errorMsg.classList.add('hidden');

        // Loading State
        elements.fetchBtn.disabled = true;
        elements.fetchSpinner.classList.remove('hidden');
        elements.fetchBtnText.textContent = 'Processing...';

        try {
            const res = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to fetch media information.');

            // Populate UI with data
            elements.mediaThumb.src = data.thumbnail || 'https://via.placeholder.com/150?text=No+Thumb';
            elements.mediaTitle.textContent = data.title;
            elements.mediaSource.textContent = data.extractor || 'Link';

            if (data.duration) {
                const m = Math.floor(data.duration / 60);
                const s = data.duration % 60;
                elements.mediaDuration.textContent = `${m}:${s.toString().padStart(2, '0')}`;
                elements.mediaDuration.classList.remove('hidden');
            } else {
                elements.mediaDuration.classList.add('hidden');
            }

            // Auto-fallback to audio if soundcloud
            const isAudioOnly = (data.extractor || '').toLowerCase().includes('soundcloud');
            if (isAudioOnly && state.type !== 'audio') {
                elements.segmentBtns[1].click();
            }

            // UI Flow Action: Hide form, reveal populated results and options
            elements.formContainer.classList.add('hidden');
            elements.resultView.classList.remove('hidden');
            elements.optionsView.classList.remove('hidden');
            elements.postDownloadView.classList.add('hidden');

        } catch (err) {
            elements.errorMsg.textContent = err.message;
            elements.errorMsg.classList.remove('hidden');
        } finally {
            elements.fetchBtn.disabled = false;
            elements.fetchSpinner.classList.add('hidden');
            elements.fetchBtnText.textContent = 'Next';
        }
    });

    // Step 2 -> Step 3: Action Download Flow
    elements.downloadBtn.addEventListener('click', () => {
        if (!state.currentUrl) return;

        const params = new URLSearchParams({
            url: state.currentUrl,
            type: state.type,
            quality: state.quality
        });

        // Trigger file download via browser native behavior
        window.location.href = `/api/download?${params.toString()}`;

        // UI Flow Action: Hide options layout, swap in post-download status
        elements.optionsView.classList.add('hidden');
        elements.postDownloadView.classList.remove('hidden');

        // Clip title length gracefully for status text
        let shortTitle = elements.mediaTitle.textContent;
        if (shortTitle.length > 35) shortTitle = shortTitle.substring(0, 35) + '...';
        elements.statusTitle.textContent = shortTitle;
    });

    // Step 3 -> Return to Step 1: Process Another Link
    elements.resetBtn.addEventListener('click', () => {
        state.currentUrl = '';
        elements.input.value = '';

        // Revert UI to initial layout
        elements.resultView.classList.add('hidden');
        elements.postDownloadView.classList.add('hidden');
        elements.optionsView.classList.remove('hidden'); // ready for next request
        elements.formContainer.classList.remove('hidden');

        elements.input.focus();
    });

    // Initial setup
    renderDropdownOptions();
});
