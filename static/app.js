/**
 * Khmer OCR Web UI — Client-Side Logic
 * ======================================
 * Handles file upload, processing, progress, and results display.
 */

// ============================================================
// STATE
// ============================================================
const state = {
    fileId: null,
    filename: null,
    preset: 'auto',
    useAi: false,
    result: null,
    rawTexts: {},      // page -> raw text
    correctedTexts: {} // page -> corrected text
};

// ============================================================
// DOM REFS
// ============================================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    dropZone:        $('#drop-zone'),
    fileInput:       $('#file-input'),
    uploadIcon:      $('#upload-icon'),
    uploadSpinner:   $('#upload-spinner'),
    uploadText:      $('#upload-text'),
    uploadHint:      $('#upload-hint'),
    docList:         $('#doc-list'),
    filePreview:     $('#file-preview'),
    previewName:     $('#preview-filename'),
    previewSize:     $('#preview-size'),
    btnRemove:       $('#btn-remove'),
    settingsSection: $('#settings-section'),
    presetOptions:   $('#preset-options'),
    aiToggle:        $('#ai-toggle'),
    btnProcess:      $('#btn-process'),
    progressSection: $('#progress-section'),
    progressSpinner: $('#progress-spinner'),
    progressHeading: $('#progress-heading'),
    progressBar:     $('#progress-bar'),
    progressPercent: $('#progress-percent'),
    progressLog:     $('#progress-log'),
    progressSub:     $('#progress-subtitle'),
    resultsSection:  $('#results-section'),
    resultsSub:      $('#results-subtitle'),
    statPages:       $('#stat-pages'),
    statChars:       $('#stat-chars'),
    statQuality:     $('#stat-quality'),
    statFixed:       $('#stat-fixed'),
    tabGroup:        $('#tab-group'),
    textOutput:      $('#text-output'),
    btnCopy:            $('#btn-copy'),
    btnDownload:        $('#btn-download'),
    pageDetails:        $('#page-details-content'),
    btnNew:             $('#btn-new'),
    uploadSection:      $('#upload-section'),
    fixBtnWrap:         $('#fix-btn-wrap'),
    fixBtn:             $('#fix-btn'),
    correctionPopover:  $('#correction-popover'),
    correctionOriginal: $('#correction-original'),
    correctionResult:   $('#correction-result'),
    btnAccept:          $('#btn-accept'),
    btnDismiss:         $('#btn-dismiss')
};

// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
    bindEvents();
});

function bindEvents() {
    initAiCorrection();
    // Drag & Drop
    els.dropZone.addEventListener('click', () => els.fileInput.click());
    els.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        els.dropZone.classList.add('drag-over');
    });
    els.dropZone.addEventListener('dragleave', () => {
        els.dropZone.classList.remove('drag-over');
    });
    els.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        els.dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    els.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFile(e.target.files[0]);
    });

    // Remove file
    els.btnRemove.addEventListener('click', resetUpload);

    // Preset buttons
    els.presetOptions.addEventListener('click', (e) => {
        const btn = e.target.closest('.preset-btn');
        if (!btn) return;
        $$('.preset-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.preset = btn.dataset.preset;
    });

    // AI toggle
    els.aiToggle.addEventListener('change', (e) => {
        state.useAi = e.target.checked;
    });

    // Process button
    els.btnProcess.addEventListener('click', startProcessing);

    // Tabs
    els.tabGroup.addEventListener('click', (e) => {
        const tab = e.target.closest('.tab');
        if (!tab) return;
        $$('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        showTab(tab.dataset.tab);
    });

    // Copy & Download
    els.btnCopy.addEventListener('click', copyText);
    els.btnDownload.addEventListener('click', downloadText);

    // New document
    els.btnNew.addEventListener('click', resetAll);
}

// ============================================================
// LOAD EXISTING DOCUMENTS
// ============================================================
async function loadDocuments() {
    try {
        const res = await fetch('/documents');
        const docs = await res.json();
        if (docs.length === 0) {
            els.docList.innerHTML = '<p class="text-muted" style="text-align:center;padding:1rem;font-size:0.8rem;">No PDFs in Document/ folder</p>';
            return;
        }
        els.docList.innerHTML = docs.map(d => `
            <div class="doc-item" data-name="${d.name}">
                <span class="doc-item-icon">📄</span>
                <span class="doc-item-name">${d.name}</span>
                <span class="doc-item-size">${formatSize(d.size)}</span>
            </div>
        `).join('');

        // Click handlers
        $$('.doc-item').forEach(item => {
            item.addEventListener('click', () => selectLocalDoc(item.dataset.name));
        });
    } catch (e) {
        els.docList.innerHTML = '<p class="text-muted" style="text-align:center;padding:0.5rem;font-size:0.8rem;">Could not load documents</p>';
    }
}

async function selectLocalDoc(filename) {
    try {
        const res = await fetch('/process-local', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }

        state.fileId = data.file_id;
        state.filename = data.filename;
        showFilePreview(data.filename, data.size);
    } catch (e) {
        alert('Failed to select document');
    }
}

// ============================================================
// FILE UPLOAD
// ============================================================
async function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Please upload a PDF file.');
        return;
    }
    if (file.size > 20 * 1024 * 1024) {
        alert('File too large. Max 20MB.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    // Show upload spinner
    els.uploadIcon.style.display = 'none';
    els.uploadSpinner.style.display = 'flex';
    els.uploadText.textContent = 'Uploading...';
    els.uploadHint.textContent = file.name;
    els.dropZone.style.pointerEvents = 'none';

    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            resetUploadSpinner();
            return;
        }

        state.fileId = data.file_id;
        state.filename = data.filename;
        showFilePreview(data.filename, data.size);
    } catch (e) {
        alert('Upload failed. Please try again.');
        resetUploadSpinner();
    }
}

function resetUploadSpinner() {
    els.uploadIcon.style.display = '';
    els.uploadSpinner.style.display = 'none';
    els.uploadText.textContent = 'Drop your PDF here';
    els.uploadHint.textContent = 'or click to browse • Max 20MB';
    els.dropZone.style.pointerEvents = '';
}

function showFilePreview(name, size) {
    els.previewName.textContent = name;
    els.previewSize.textContent = formatSize(size);
    els.filePreview.style.display = 'flex';
    els.dropZone.style.display = 'none';
    els.settingsSection.style.display = '';
    els.settingsSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function resetUpload() {
    state.fileId = null;
    state.filename = null;
    els.filePreview.style.display = 'none';
    els.dropZone.style.display = '';
    els.dropZone.style.pointerEvents = '';
    els.dropZone.style.opacity = '';
    els.settingsSection.style.display = 'none';
    els.fileInput.value = '';
}

// ============================================================
// PROCESSING (SSE)
// ============================================================
async function startProcessing() {
    if (!state.fileId) return;

    // Show progress, hide others
    els.settingsSection.style.display = 'none';
    els.uploadSection.style.display = 'none';
    els.progressSection.style.display = '';
    els.resultsSection.style.display = 'none';
    els.btnProcess.disabled = true;

    // Reset progress
    els.progressBar.style.width = '0%';
    els.progressPercent.textContent = '0%';
    els.progressLog.innerHTML = '';
    els.progressSpinner.style.display = '';
    els.progressHeading.textContent = 'Processing';

    els.progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
        const res = await fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_id: state.fileId,
                preset: state.preset,
                use_ai: state.useAi
            })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // keep incomplete chunk

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleProgressEvent(data);
                    } catch (e) {
                        // skip malformed
                    }
                }
            }
        }
    } catch (e) {
        addLogLine('❌ Connection error: ' + e.message);
    }

    els.btnProcess.disabled = false;
}

function handleProgressEvent(data) {
    // Update log
    if (data.message) {
        addLogLine(data.message);
    }

    // Update progress bar
    if (data.progress !== undefined) {
        els.progressBar.style.width = data.progress + '%';
        els.progressPercent.textContent = data.progress + '%';
    }

    // On converting
    if (data.step === 'converting') {
        els.progressBar.style.width = '5%';
        els.progressPercent.textContent = '5%';
    }

    // Store page data
    if (data.step === 'page_done' && data.page) {
        // Will be fully populated on complete
    }

    // AI step
    if (data.step === 'ai_correction') {
        els.progressBar.style.width = '90%';
        els.progressPercent.textContent = '90%';
        els.progressSub.textContent = 'Running AI correction...';
    }

    // Complete!
    if (data.step === 'complete' && data.result) {
        els.progressBar.style.width = '100%';
        els.progressPercent.textContent = '100%';

        // Stop the header spinner, show checkmark
        els.progressSpinner.style.display = 'none';
        els.progressHeading.textContent = 'Done';

        // Mark last log line as done
        const last = els.progressLog.querySelector('.log-line.log-active');
        if (last) {
            last.classList.remove('log-active');
            last.classList.add('log-done');
            last.querySelector('.log-icon').textContent = '✓';
        }

        setTimeout(() => showResults(data.result), 600);
    }

    // Error
    if (data.step === 'error') {
        els.progressSpinner.style.display = 'none';
        els.progressHeading.textContent = 'Failed';
        const last = els.progressLog.querySelector('.log-line.log-active');
        if (last) {
            last.classList.remove('log-active');
            last.querySelector('.log-icon').textContent = '✕';
        }
    }
}

function addLogLine(msg) {
    // Mark previous active line as done
    const prev = els.progressLog.querySelector('.log-line.log-active');
    if (prev) {
        prev.classList.remove('log-active');
        prev.classList.add('log-done');
        prev.querySelector('.log-icon').textContent = '✓';
    }

    const div = document.createElement('div');
    div.className = 'log-line log-active';

    const icon = document.createElement('span');
    icon.className = 'log-icon';
    // spinner is rendered via CSS on .log-active — no text needed
    icon.textContent = '';

    const text = document.createElement('span');
    text.className = 'log-text';
    text.textContent = msg;

    div.appendChild(icon);
    div.appendChild(text);
    els.progressLog.appendChild(div);
    els.progressLog.scrollTop = els.progressLog.scrollHeight;
}

// ============================================================
// RESULTS DISPLAY
// ============================================================
function showResults(result) {
    state.result = result;

    // Hide progress, show results
    els.progressSection.style.display = 'none';
    els.resultsSection.style.display = '';

    // Subtitle
    els.resultsSub.textContent = `${result.filename} • ${result.total_pages} page(s)`;

    // Stats
    els.statPages.textContent = result.total_pages;
    els.statChars.textContent = formatNumber(result.full_text.length);

    // Quality — show most common
    if (result.pages && result.pages.length > 0) {
        const types = result.pages.map(p => p.quality?.recommended_preset || '—');
        const mostCommon = mode(types);
        els.statQuality.textContent = capitalize(mostCommon);
    }

    // Lines fixed
    const totalFixed = result.pages
        ? result.pages.reduce((sum, p) => sum + (p.lines_removed || 0), 0)
        : 0;
    els.statFixed.textContent = totalFixed;

    // Store text data
    state.correctedTexts = {};
    state.rawTexts = {};
    if (result.pages) {
        result.pages.forEach(p => {
            state.correctedTexts[p.page] = p.text;
        });
    }

    // Show corrected text
    els.textOutput.textContent = result.full_text;

    // Page details
    if (result.pages) {
        els.pageDetails.innerHTML = result.pages.map(p => `
            <div class="page-quality-card">
                <h4>📄 Page ${p.page}</h4>
                <div class="quality-row">
                    <span>Type</span>
                    <span>${capitalize(p.quality?.recommended_preset || '—')}</span>
                </div>
                <div class="quality-row">
                    <span>Noise</span>
                    <span>${p.quality?.noise_level ?? '—'}</span>
                </div>
                <div class="quality-row">
                    <span>Contrast</span>
                    <span>${p.quality?.contrast ?? '—'}</span>
                </div>
                <div class="quality-row">
                    <span>White %</span>
                    <span>${p.quality?.white_ratio ?? '—'}%</span>
                </div>
                <div class="quality-row">
                    <span>Lines Fixed</span>
                    <span>${p.lines_removed || 0}</span>
                </div>
                <div class="quality-row">
                    <span>Characters</span>
                    <span>${formatNumber(p.char_count || 0)}</span>
                </div>
            </div>
        `).join('');
    }

    els.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showTab(tab) {
    if (!state.result) return;
    if (tab === 'corrected') {
        els.textOutput.textContent = state.result.full_text;
    } else if (tab === 'raw') {
        // Compile raw text from pages
        if (state.result.pages) {
            // Raw text isn't sent back in the SSE to save bandwidth
            // We just show a note
            els.textOutput.textContent = state.result.full_text + '\n\n(Raw OCR view shows the same text — raw data is available in exported file)';
        }
    }
}

// ============================================================
// COPY & DOWNLOAD
// ============================================================
async function copyText() {
    if (!state.result) return;
    try {
        await navigator.clipboard.writeText(state.result.full_text);
        els.btnCopy.textContent = '✅ Copied!';
        els.btnCopy.classList.add('copy-success');
        setTimeout(() => {
            els.btnCopy.textContent = '📋 Copy';
            els.btnCopy.classList.remove('copy-success');
        }, 2000);
    } catch (e) {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = state.result.full_text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        els.btnCopy.textContent = '✅ Copied!';
        setTimeout(() => { els.btnCopy.textContent = '📋 Copy'; }, 2000);
    }
}

function downloadText() {
    if (!state.result) return;
    window.location.href = `/download/${state.result.file_id}`;
}

// ============================================================
// RESET
// ============================================================
function resetAll() {
    state.fileId = null;
    state.filename = null;
    state.result = null;
    state.rawTexts = {};
    state.correctedTexts = {};

    els.uploadSection.style.display = '';
    els.filePreview.style.display = 'none';
    els.dropZone.style.display = '';
    els.dropZone.style.pointerEvents = '';
    els.dropZone.style.opacity = '';
    els.settingsSection.style.display = 'none';
    els.progressSection.style.display = 'none';
    els.resultsSection.style.display = 'none';
    els.fileInput.value = '';

    // Reset tabs
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.tab')[0]?.classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================================
// AI TEXT CORRECTION (Claude API)
// ============================================================
let _currentSelection = null;  // { text, start, end } in textOutput

function initAiCorrection() {
    // Show fix button when user selects text in the output
    document.addEventListener('mouseup', (e) => {
        const selection = window.getSelection();
        const selected  = selection.toString().trim();

        // Only trigger if selection is inside the text output
        if (!selected || !els.textOutput.contains(selection.anchorNode)) {
            els.fixBtnWrap.style.display = 'none';
            return;
        }

        const range = selection.getRangeAt(0);
        const rect  = range.getBoundingClientRect();

        // Position the button just above the selection
        els.fixBtnWrap.style.display = 'block';
        els.fixBtnWrap.style.left = (rect.left + rect.width / 2 - 70) + 'px';
        els.fixBtnWrap.style.top  = (rect.top + window.scrollY - 42) + 'px';

        _currentSelection = { text: selected };
    });

    // Hide button when clicking elsewhere
    document.addEventListener('mousedown', (ev) => {
        if (!els.fixBtnWrap.contains(ev.target)) {
            els.fixBtnWrap.style.display = 'none';
        }
    });

    els.fixBtn.addEventListener('click', runAiCorrection);
    els.btnDismiss.addEventListener('click', () => {
        els.correctionPopover.style.display = 'none';
    });
    els.btnAccept.addEventListener('click', acceptCorrection);
}

async function runAiCorrection() {
    if (!_currentSelection) return;

    const selected = _currentSelection.text;
    const fullText = els.textOutput.textContent;
    const idx      = fullText.indexOf(selected);

    // Grab ~300 chars of surrounding context
    const ctxStart = Math.max(0, idx - 150);
    const ctxEnd   = Math.min(fullText.length, idx + selected.length + 150);
    const context  = fullText.slice(ctxStart, ctxEnd);

    // Show popover in loading state
    els.fixBtnWrap.style.display = 'none';
    els.correctionOriginal.textContent = selected;
    els.correctionResult.textContent   = '';
    els.correctionResult.classList.add('loading-text');
    els.btnAccept.disabled = true;
    els.correctionPopover.style.display = 'block';

    try {
        const res  = await fetch('/correct', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected_text: selected, context })
        });
        const data = await res.json();

        els.correctionResult.classList.remove('loading-text');

        if (data.error) {
            els.correctionResult.textContent = '❌ ' + data.error;
        } else {
            els.correctionResult.textContent = data.corrected;
            els.btnAccept.disabled = false;
            _currentSelection.corrected = data.corrected;
        }
    } catch (e) {
        els.correctionResult.classList.remove('loading-text');
        els.correctionResult.textContent = '❌ Request failed: ' + e.message;
    }
}

function acceptCorrection() {
    if (!_currentSelection?.corrected) return;

    // Replace in the displayed text
    const old     = _currentSelection.text;
    const fixed   = _currentSelection.corrected;
    const current = els.textOutput.textContent;
    els.textOutput.textContent = current.replace(old, fixed);

    // Also update in state so Download/Copy use the corrected version
    if (state.result) {
        state.result.full_text = state.result.full_text.replace(old, fixed);
    }

    els.correctionPopover.style.display = 'none';
    _currentSelection = null;
}

// ============================================================
// UTILITIES
// ============================================================
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatNumber(n) {
    return n.toLocaleString();
}

function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function mode(arr) {
    const counts = {};
    arr.forEach(v => counts[v] = (counts[v] || 0) + 1);
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';
}
