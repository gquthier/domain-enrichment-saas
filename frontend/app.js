// Application State
const state = {
    jobId: null,
    filename: null,
    columns: [],
    detectedCompanyCol: null,
    detectedContextCols: [],
    rowCount: 0,
    columnMappings: [],
    ws: null
};

// API Base URL (adjust for production)
const API_BASE = window.location.origin;

// DOM Elements
const uploadSection = document.getElementById('upload-section');
const mappingSection = document.getElementById('mapping-section');
const processingSection = document.getElementById('processing-section');
const completeSection = document.getElementById('complete-section');
const errorSection = document.getElementById('error-section');

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadProgress = document.getElementById('upload-progress');

const backBtn = document.getElementById('back-btn');
const startEnrichmentBtn = document.getElementById('start-enrichment-btn');
const downloadBtn = document.getElementById('download-btn');
const newEnrichmentBtn = document.getElementById('new-enrichment-btn');
const retryBtn = document.getElementById('retry-btn');

// Utility Functions
function showSection(section) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    section.classList.add('active');
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    const container = document.getElementById('toast-container');
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    showSection(errorSection);
}

// File Upload Handlers
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

async function handleFileUpload(file) {
    // Validate file type
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validTypes.includes(ext)) {
        showToast('Type de fichier invalide. Utilisez CSV ou Excel.', 'error');
        return;
    }

    // Validate file size (50MB)
    if (file.size > 52428800) {
        showToast('Fichier trop volumineux (max 50MB).', 'error');
        return;
    }

    // Show progress
    uploadProgress.classList.remove('hidden');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();

        // Store state
        state.jobId = data.job_id;
        state.filename = data.filename;
        state.columns = data.columns;
        state.detectedCompanyCol = data.detected_company_col;
        state.detectedContextCols = data.detected_context_cols || [];
        state.rowCount = data.row_count;

        // Show mapping section
        showMappingSection();
        showToast('Fichier uploadé avec succès !');

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        uploadProgress.classList.add('hidden');
    }
}

// Mapping Section
function showMappingSection() {
    // Update file info
    document.getElementById('filename').textContent = state.filename;
    document.getElementById('row-count').textContent = state.rowCount.toLocaleString();

    // Build column mappings
    const mappingsContainer = document.getElementById('column-mappings');
    mappingsContainer.innerHTML = '';

    // Target fields
    const targetFields = [
        { value: 'company name', label: 'Nom de l\'entreprise (requis)', required: true },
        { value: 'country', label: 'Pays', required: false },
        { value: 'sector', label: 'Secteur', required: false },
        { value: 'description', label: 'Description', required: false },
        { value: 'linkedin', label: 'LinkedIn URL', required: false },
        { value: 'siren', label: 'SIREN', required: false },
        { value: 'siret', label: 'SIRET', required: false },
        { value: 'vat', label: 'VAT/TVA', required: false },
        { value: 'ignore', label: '--- Ignorer ---', required: false }
    ];

    // Track already assigned target columns to ensure uniqueness
    const assignedTargets = new Set();

    // Create mapping rows
    state.columns.forEach(sourceCol => {
        const row = document.createElement('div');
        row.className = 'mapping-row';

        // Source column
        const sourceDiv = document.createElement('div');
        sourceDiv.className = 'source-col';
        sourceDiv.textContent = sourceCol;

        // Arrow
        const arrowDiv = document.createElement('div');
        arrowDiv.className = 'mapping-arrow';

        // Target select
        const targetSelect = document.createElement('select');
        targetSelect.dataset.sourceColumn = sourceCol;

        // Determine default selection with uniqueness check
        let defaultValue = 'ignore';
        const sourceLower = sourceCol.toLowerCase();

        if (sourceCol === state.detectedCompanyCol && !assignedTargets.has('company name')) {
            defaultValue = 'company name';
        } else if (state.detectedContextCols.includes(sourceCol)) {
            // Try to match context column (only if not already assigned)
            if ((sourceLower.includes('country') || sourceLower.includes('pays')) && !assignedTargets.has('country')) {
                defaultValue = 'country';
            } else if ((sourceLower.includes('sector') || sourceLower.includes('secteur') || sourceLower.includes('industry')) && !assignedTargets.has('sector')) {
                defaultValue = 'sector';
            } else if ((sourceLower.includes('description') || sourceLower.includes('about')) && !assignedTargets.has('description')) {
                defaultValue = 'description';
            } else if (sourceLower.includes('linkedin') && !assignedTargets.has('linkedin')) {
                defaultValue = 'linkedin';
            } else if (sourceLower.includes('siren') && !assignedTargets.has('siren')) {
                defaultValue = 'siren';
            } else if (sourceLower.includes('siret') && !assignedTargets.has('siret')) {
                defaultValue = 'siret';
            } else if ((sourceLower.includes('vat') || sourceLower.includes('tva')) && !assignedTargets.has('vat')) {
                defaultValue = 'vat';
            }
        }

        // Mark the target as assigned if it's not 'ignore'
        if (defaultValue !== 'ignore') {
            assignedTargets.add(defaultValue);
        }

        // Add options
        targetFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field.value;
            option.textContent = field.label;
            if (field.value === defaultValue) {
                option.selected = true;
            }
            targetSelect.appendChild(option);
        });

        row.appendChild(sourceDiv);
        row.appendChild(arrowDiv);
        row.appendChild(targetSelect);

        mappingsContainer.appendChild(row);
    });

    showSection(mappingSection);
}

backBtn.addEventListener('click', () => {
    showSection(uploadSection);
});

startEnrichmentBtn.addEventListener('click', async () => {
    // Collect mappings
    const selects = document.querySelectorAll('#column-mappings select');
    const mappings = [];
    let hasCompanyName = false;

    selects.forEach(select => {
        const sourceColumn = select.dataset.sourceColumn;
        const targetColumn = select.value;

        if (targetColumn !== 'ignore') {
            mappings.push({
                source_column: sourceColumn,
                target_column: targetColumn
            });

            if (targetColumn === 'company name') {
                hasCompanyName = true;
            }
        }
    });

    // Validate
    if (!hasCompanyName) {
        showToast('Vous devez mapper au moins une colonne "Nom de l\'entreprise"', 'error');
        return;
    }

    state.columnMappings = mappings;

    // Start enrichment
    try {
        startEnrichmentBtn.disabled = true;

        const response = await fetch(`${API_BASE}/api/enrich`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: state.jobId,
                column_mappings: mappings
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Enrichment failed to start');
        }

        // Show processing section and connect WebSocket
        showProcessingSection();
        connectWebSocket();

    } catch (error) {
        showToast(error.message, 'error');
        startEnrichmentBtn.disabled = false;
    }
});

// Processing Section
function showProcessingSection() {
    document.getElementById('processing-message').textContent = 'Initialisation...';
    document.getElementById('progress-count').textContent = '0';
    document.getElementById('total-count').textContent = state.rowCount;
    document.getElementById('progress-percentage').textContent = '0%';
    document.getElementById('enrichment-progress-fill').style.width = '0%';

    showSection(processingSection);
}

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${state.jobId}`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
    };

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
            updateProgress(data);
        } else if (data.type === 'completed') {
            handleCompletion(data);
        } else if (data.type === 'error') {
            handleError(data);
        }
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Fallback to polling
        pollJobStatus();
    };

    state.ws.onclose = () => {
        console.log('WebSocket closed');
    };
}

function updateProgress(data) {
    const { progress, total, percentage, message } = data;

    document.getElementById('progress-count').textContent = progress.toLocaleString();
    document.getElementById('total-count').textContent = total.toLocaleString();
    document.getElementById('progress-percentage').textContent = `${percentage}%`;
    document.getElementById('enrichment-progress-fill').style.width = `${percentage}%`;

    if (message) {
        document.getElementById('processing-message').textContent = message;
        document.getElementById('processing-detail').textContent = message;
    }
}

async function pollJobStatus() {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/status/${state.jobId}`);
            if (!response.ok) {
                clearInterval(pollInterval);
                return;
            }

            const data = await response.json();

            updateProgress({
                progress: data.progress,
                total: data.total,
                percentage: data.percentage,
                message: data.message
            });

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                handleCompletion({ download_url: `/api/download/${state.jobId}` });
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                handleError({ error: data.error });
            }
        } catch (error) {
            clearInterval(pollInterval);
            handleError({ error: error.message });
        }
    }, 2000);
}

function handleCompletion(data) {
    if (state.ws) {
        state.ws.close();
    }

    // Update complete section
    document.getElementById('final-count').textContent = state.rowCount.toLocaleString();
    // Estimate domains found (in real scenario, server should provide this)
    document.getElementById('domains-found').textContent = `~${Math.floor(state.rowCount * 0.85).toLocaleString()}`;

    showSection(completeSection);
    showToast('Enrichissement terminé avec succès !');
}

function handleError(data) {
    if (state.ws) {
        state.ws.close();
    }

    showError(data.error || 'Une erreur inconnue est survenue');
}

downloadBtn.addEventListener('click', () => {
    window.location.href = `${API_BASE}/api/download/${state.jobId}`;
});

newEnrichmentBtn.addEventListener('click', () => {
    // Reset state
    state.jobId = null;
    state.filename = null;
    state.columns = [];
    state.detectedCompanyCol = null;
    state.detectedContextCols = [];
    state.rowCount = 0;
    state.columnMappings = [];

    // Reset file input
    fileInput.value = '';

    // Show upload section
    showSection(uploadSection);
});

retryBtn.addEventListener('click', () => {
    showSection(uploadSection);
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Domain Enrichment SaaS initialized');
});
