/**
 * FakeBuster AI — Frontend Application
 * SPA with API client, JWT auth, routing, file upload, and analysis display.
 */

// ═══════════════════════════════════════
// Configuration
// ═══════════════════════════════════════
const API_BASE = 'http://localhost:8000/api/v1';

// ═══════════════════════════════════════
// State
// ═══════════════════════════════════════
const state = {
    token: localStorage.getItem('fb_token') || null,
    user: JSON.parse(localStorage.getItem('fb_user') || 'null'),
    currentPage: 'landing',
    analyses: [],
    currentFilter: '',
    currentPageNum: 1,
    pageSize: 10,
    totalAnalyses: 0,
};

// ═══════════════════════════════════════
// API Client
// ═══════════════════════════════════════
async function api(endpoint, options = {}) {
    const headers = { ...options.headers };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    if (options.json) {
        headers['Content-Type'] = 'application/json';
    }

    const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: options.method || 'GET',
        headers,
        body: options.json ? JSON.stringify(options.json) : options.body,
    });

    const data = await resp.json().catch(() => null);

    if (!resp.ok) {
        // Handle token expiration / auth errors — auto-logout
        if (resp.status === 401) {
            const detail = data?.detail || '';
            if (detail.includes('expired') || detail.includes('Invalid') || detail.includes('Authentication')) {
                toast('Session expired — please sign in again', 'warning');
                logout();
                throw new Error('Session expired');
            }
        }
        const msg = data?.detail || data?.message || `Request failed (${resp.status})`;
        throw new Error(msg);
    }
    return data;
}

// ── Auth API ──
async function apiRegister(email, password) {
    return api('/auth/register', { method: 'POST', json: { email, password } });
}

async function apiLogin(email, password) {
    const data = await api('/auth/login', { method: 'POST', json: { email, password } });
    state.token = data.access_token;
    localStorage.setItem('fb_token', data.access_token);
    // Fetch user info
    const user = await api('/auth/me');
    state.user = user;
    localStorage.setItem('fb_user', JSON.stringify(user));
    return user;
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('fb_token');
    localStorage.removeItem('fb_user');
    navigate('landing');
}

// ── Upload API ──
async function apiUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    return api('/upload', { method: 'POST', body: formData });
}

// ── URL Ingest API ──
async function apiIngestUrl(url) {
    return api('/ingest/url', { method: 'POST', json: { url } });
}

// ── Analysis API ──
async function apiGetAnalyses(page = 1, statusFilter = '') {
    let endpoint = `/analysis?page=${page}&page_size=${state.pageSize}`;
    if (statusFilter) endpoint += `&status=${statusFilter}`;
    return api(endpoint);
}

async function apiGetAnalysis(id) {
    return api(`/analysis/${id}`);
}

// ═══════════════════════════════════════
// Router
// ═══════════════════════════════════════
function navigate(page, data = {}) {
    // Auth guard
    const protectedPages = ['dashboard', 'analysis'];
    if (protectedPages.includes(page) && !state.token) {
        page = 'login';
    }

    // Redirect logged-in users away from auth pages
    if (['landing', 'login', 'register'].includes(page) && state.token) {
        page = 'dashboard';
    }

    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) {
        target.classList.add('active');
        state.currentPage = page;
    }

    // Page-specific logic
    if (page === 'dashboard') {
        loadDashboard();
    } else if (page === 'analysis' && data.id) {
        loadAnalysisDetail(data.id);
    }

    // Update nav
    updateNav();
    window.scrollTo(0, 0);
}

function updateNav() {
    const navLinks = document.getElementById('nav-links');
    if (state.token && state.user) {
        navLinks.innerHTML = `
            <span class="nav-user-email" style="color: var(--text-secondary); font-size: 0.84rem; margin-right: 8px;">
                ${state.user.email}
            </span>
            <button class="btn btn-ghost btn-sm" data-navigate="dashboard">Dashboard</button>
            <button class="btn btn-danger btn-sm" id="logout-btn">Logout</button>
        `;
        document.getElementById('logout-btn').addEventListener('click', logout);
    } else {
        navLinks.innerHTML = `
            <button class="btn btn-ghost btn-sm" data-navigate="login">Sign In</button>
            <button class="btn btn-primary btn-sm" data-navigate="register">Get Started</button>
        `;
    }
    // Rebind nav buttons
    navLinks.querySelectorAll('[data-navigate]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            navigate(btn.dataset.navigate);
        });
    });
}

// ═══════════════════════════════════════
// Auth Handlers
// ═══════════════════════════════════════
function initAuth() {
    // Login form
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('login-btn');
        const error = document.getElementById('login-error');
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        setLoading(btn, true);
        error.classList.add('hidden');

        try {
            await apiLogin(email, password);
            toast('Welcome back!', 'success');
            navigate('dashboard');
        } catch (err) {
            error.textContent = err.message;
            error.classList.remove('hidden');
        } finally {
            setLoading(btn, false);
        }
    });

    // Register form
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('register-btn');
        const error = document.getElementById('register-error');
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        const confirm = document.getElementById('reg-confirm').value;

        if (password !== confirm) {
            error.textContent = 'Passwords do not match';
            error.classList.remove('hidden');
            return;
        }

        setLoading(btn, true);
        error.classList.add('hidden');

        try {
            await apiRegister(email, password);
            await apiLogin(email, password);
            toast('Account created! Welcome to FakeBuster AI', 'success');
            navigate('dashboard');
        } catch (err) {
            error.textContent = err.message;
            error.classList.remove('hidden');
        } finally {
            setLoading(btn, false);
        }
    });
}

// ═══════════════════════════════════════
// Dashboard
// ═══════════════════════════════════════
async function loadDashboard() {
    // Update greeting
    if (state.user) {
        document.getElementById('user-greeting').textContent =
            `Welcome back, ${state.user.email}`;
    }
    await loadAnalyses();
}

async function loadAnalyses() {
    try {
        const data = await apiGetAnalyses(state.currentPageNum, state.currentFilter);
        state.analyses = data.items;
        state.totalAnalyses = data.total;
        renderAnalysesList(data.items);
        renderPagination(data.total, data.page, data.page_size);
    } catch (err) {
        console.error('Failed to load analyses:', err);
        if (err.message.includes('401') || err.message.includes('Authentication')) {
            logout();
        }
    }
}

function renderAnalysesList(analyses) {
    const container = document.getElementById('analyses-list');

    if (!analyses || analyses.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
                </svg>
                <p>No analyses yet. Upload a file or submit a URL to get started.</p>
            </div>`;
        return;
    }

    container.innerHTML = analyses.map(a => {
        const shortId = a.id.substring(0, 8);
        const date = a.created_at ? formatDate(a.created_at) : '';
        const scoreText = a.result_score != null ? (a.result_score * 100).toFixed(1) + '%' : '—';
        const typeClass = a.source_type === 'upload' ? 'upload' : 'url';
        const typeIcon = a.source_type === 'upload' ? '↑' : '🔗';

        return `
            <div class="analysis-row" data-analysis-id="${a.id}">
                <div class="analysis-type-icon ${typeClass}">${typeIcon}</div>
                <div class="analysis-info">
                    <div class="analysis-id">${shortId}…</div>
                    <div class="analysis-date">${date}</div>
                </div>
                <span class="analysis-media-type">${a.media_type}</span>
                <span class="status-badge ${a.status}">${a.status}</span>
                <span class="analysis-score">${scoreText}</span>
            </div>`;
    }).join('');

    // Click handlers
    container.querySelectorAll('.analysis-row').forEach(row => {
        row.addEventListener('click', () => {
            navigate('analysis', { id: row.dataset.analysisId });
        });
    });
}

function renderPagination(total, page, pageSize) {
    const pag = document.getElementById('pagination');
    const totalPages = Math.ceil(total / pageSize);

    if (totalPages <= 1) {
        pag.classList.add('hidden');
        return;
    }

    pag.classList.remove('hidden');
    document.getElementById('page-info').textContent = `Page ${page} of ${totalPages}`;
    document.getElementById('prev-page-btn').disabled = page <= 1;
    document.getElementById('next-page-btn').disabled = page >= totalPages;
}

function initDashboard() {
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentFilter = btn.dataset.filter;
            state.currentPageNum = 1;
            loadAnalyses();
        });
    });

    // Pagination
    document.getElementById('prev-page-btn').addEventListener('click', () => {
        if (state.currentPageNum > 1) {
            state.currentPageNum--;
            loadAnalyses();
        }
    });
    document.getElementById('next-page-btn').addEventListener('click', () => {
        state.currentPageNum++;
        loadAnalyses();
    });

    // Refresh
    document.getElementById('refresh-analyses-btn').addEventListener('click', loadAnalyses);

    // File upload — dropzone
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // URL form
    document.getElementById('url-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const urlInput = document.getElementById('url-input');
        const btn = document.getElementById('url-submit-btn');
        const error = document.getElementById('url-error');

        setLoading(btn, true);
        error.classList.add('hidden');

        try {
            const result = await apiIngestUrl(urlInput.value);
            toast('URL submitted for analysis!', 'success');
            urlInput.value = '';
            loadAnalyses();
            // Poll for completion
            pollAnalysis(result.id);
        } catch (err) {
            error.textContent = err.message;
            error.classList.remove('hidden');
        } finally {
            setLoading(btn, false);
        }
    });
}

async function handleFileUpload(file) {
    const progressEl = document.getElementById('upload-progress');
    const filenameEl = document.getElementById('upload-filename');
    const statusEl = document.getElementById('upload-status');
    const fillEl = document.getElementById('upload-progress-fill');

    filenameEl.textContent = file.name;
    statusEl.textContent = 'Uploading...';
    statusEl.style.color = 'var(--accent-cyan)';
    fillEl.style.width = '0%';
    progressEl.classList.remove('hidden');

    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress = Math.min(progress + Math.random() * 15, 85);
        fillEl.style.width = progress + '%';
    }, 200);

    try {
        const result = await apiUpload(file);
        clearInterval(progressInterval);
        fillEl.style.width = '100%';
        statusEl.textContent = 'Queued for analysis';
        statusEl.style.color = 'var(--accent-green)';
        toast('File uploaded! Analysis in progress...', 'success');
        loadAnalyses();
        // Poll for result
        pollAnalysis(result.id);
    } catch (err) {
        clearInterval(progressInterval);
        fillEl.style.width = '0%';
        statusEl.textContent = 'Upload failed';
        statusEl.style.color = 'var(--accent-red)';
        toast(err.message, 'error');
    }

    // Clear progress after a delay
    setTimeout(() => {
        progressEl.classList.add('hidden');
    }, 5000);
}

async function pollAnalysis(analysisId, attempts = 0) {
    if (attempts > 30) return; // Max ~1 minute
    try {
        const analysis = await apiGetAnalysis(analysisId);
        if (analysis.status === 'done' || analysis.status === 'failed') {
            if (analysis.status === 'done') {
                const score = analysis.result_score || 0;
                const pct = (score * 100).toFixed(0);
                const verdict = analysis.result_detail?.verdict;
                const msg = verdict
                    ? verdict
                    : `Analysis complete — ${pct}% fake probability`;
                toast(msg, 'success');
            } else {
                toast('Analysis failed — please try again', 'error');
            }
            loadAnalyses();
            return;
        }
    } catch (err) {
        // Ignore polling errors
    }
    setTimeout(() => pollAnalysis(analysisId, attempts + 1), 2000);
}

// ═══════════════════════════════════════
// Analysis Detail
// ═══════════════════════════════════════
async function loadAnalysisDetail(id) {
    const container = document.getElementById('analysis-content');
    container.innerHTML = `
        <div class="empty-state" style="padding: 80px 0;">
            <div class="btn-loader" style="width: 32px; height: 32px; border-width: 3px; border-color: rgba(255,255,255,0.1); border-top-color: var(--accent-cyan);"></div>
            <p>Loading analysis...</p>
        </div>`;

    try {
        const a = await apiGetAnalysis(id);
        renderAnalysisDetail(a);
    } catch (err) {
        container.innerHTML = `
            <div class="error-card">
                <h3>Failed to load analysis</h3>
                <p>${err.message}</p>
            </div>`;
    }
}

function renderAnalysisDetail(a) {
    const container = document.getElementById('analysis-content');
    const score = a.result_score != null ? a.result_score : 0;
    const scorePercent = (score * 100).toFixed(1);
    const fakePercent = (score * 100).toFixed(0);
    const realPercent = ((1.0 - score) * 100).toFixed(0);
    const circumference = 2 * Math.PI * 56; // r=56
    const offset = circumference - (score * circumference);

    // Determine score color and risk level
    let scoreColor = 'var(--accent-green)';
    let riskLevel = 'LOW RISK';
    let riskIcon = '✓';
    let verdictShort = 'Likely Authentic';
    if (score > 0.85) {
        scoreColor = 'var(--accent-red)';
        riskLevel = 'HIGH RISK';
        riskIcon = '⚠';
        verdictShort = 'Very Likely AI-Generated';
    } else if (score > 0.65) {
        scoreColor = '#ff6b6b';
        riskLevel = 'ELEVATED RISK';
        riskIcon = '⚠';
        verdictShort = 'Probably AI-Generated';
    } else if (score > 0.45) {
        scoreColor = 'var(--accent-yellow)';
        riskLevel = 'UNCERTAIN';
        riskIcon = '?';
        verdictShort = 'Inconclusive';
    } else if (score > 0.25) {
        scoreColor = 'var(--accent-green)';
        riskLevel = 'LOW RISK';
        riskIcon = '✓';
        verdictShort = 'Mostly Authentic';
    }

    const detail = a.result_detail || {};
    const layers = detail.layers || {};
    const confidence = detail.confidence != null ? (detail.confidence * 100).toFixed(0) : '—';
    const trustScore = detail.trust_score != null ? (detail.trust_score * 100).toFixed(0) : '—';
    const verdict = detail.verdict || '';
    const mediaType = detail.media_type || a.media_type || 'image';
    const framesAnalyzed = detail.frames_analyzed || null;

    // Build the human-readable verdict banner
    let verdictBannerHTML = '';
    if (a.status === 'done') {
        const verdictText = verdict || `This ${mediaType} is ${fakePercent}% likely to be AI-generated`;
        let bannerClass = 'verdict-authentic';
        let bannerIconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>`;

        if (score > 0.65) {
            bannerClass = 'verdict-fake';
            bannerIconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
        } else if (score > 0.45) {
            bannerClass = 'verdict-uncertain';
            bannerIconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
        }

        verdictBannerHTML = `
            <div class="verdict-banner ${bannerClass}">
                <div class="verdict-icon">${bannerIconSvg}</div>
                <div class="verdict-content">
                    <div class="verdict-text">${verdictText}</div>
                    <div class="verdict-meta">
                        <span class="verdict-risk">${riskLevel}</span>
                        <span class="verdict-separator">•</span>
                        <span>Confidence: ${confidence}%</span>
                        ${framesAnalyzed ? `<span class="verdict-separator">•</span><span>${framesAnalyzed} frames analyzed</span>` : ''}
                    </div>
                </div>
            </div>`;
    }

    // Layer breakdown with enhanced visuals
    let layersHTML = '';
    const layerColors = {
        frequency_analysis: '#7c3aed',
        edge_coherence: '#00d4ff',
        texture_analysis: '#f59e0b',
        color_statistics: '#10b981',
        // Legacy layer names from old model
        spatial_cnn: '#00d4ff',
        skin_texture: '#f59e0b',
        ensemble_vit: '#10b981',
    };

    const layerDescriptions = {
        frequency_analysis: 'Spectral analysis detects unnatural frequency patterns common in AI-generated media',
        edge_coherence: 'Edge analysis measures consistency and natural variation in object boundaries',
        texture_analysis: 'Texture analysis identifies overly smooth or synthetic surface patterns',
        color_statistics: 'Color analysis checks for unnatural color distributions and correlations',
        spatial_cnn: 'Spatial analysis of visual patterns using neural network detection',
        skin_texture: 'Analysis of skin texture patterns for signs of AI generation',
        ensemble_vit: 'Vision transformer ensemble for comprehensive feature analysis',
    };

    for (const [key, val] of Object.entries(layers)) {
        const layerScore = val.score || 0;
        const layerPercent = (layerScore * 100).toFixed(1);
        const color = layerColors[key] || '#888';
        const name = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const description = layerDescriptions[key] || '';
        const weight = val.weight ? (val.weight * 100).toFixed(0) : '—';

        let layerVerdict = 'Authentic';
        let layerVerdictClass = 'layer-verdict-safe';
        if (layerScore > 0.7) { layerVerdict = 'Suspicious'; layerVerdictClass = 'layer-verdict-danger'; }
        else if (layerScore > 0.4) { layerVerdict = 'Mixed'; layerVerdictClass = 'layer-verdict-warning'; }

        layersHTML += `
            <div class="layer-detail-enhanced">
                <div class="layer-header-row">
                    <div class="layer-dot" style="background: ${color};"></div>
                    <div class="layer-info">
                        <div class="layer-name">${name}</div>
                        <div class="layer-model">${val.model || ''} ${weight !== '—' ? `• Weight: ${weight}%` : ''}</div>
                    </div>
                    <div class="layer-verdict-badge ${layerVerdictClass}">${layerVerdict}</div>
                    <div class="layer-score-val" style="color: ${color};">${layerPercent}%</div>
                </div>
                <div class="layer-progress">
                    <div class="layer-progress-fill" style="width: ${layerPercent}%; background: ${color};"></div>
                </div>
                ${description ? `<div class="layer-description">${description}</div>` : ''}
            </div>`;
    }

    container.innerHTML = `
        ${verdictBannerHTML}

        <div class="detail-header glass-card">
            <div class="score-gauge">
                <svg viewBox="0 0 128 128">
                    <circle class="gauge-bg" cx="64" cy="64" r="56"/>
                    <circle class="gauge-fill" cx="64" cy="64" r="56"
                        stroke="${scoreColor}"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${a.status === 'done' ? offset : circumference}"
                    />
                </svg>
                <div class="score-value">
                    <div class="score-number" style="color: ${scoreColor};">
                        ${a.status === 'done' ? scorePercent + '%' : '—'}
                    </div>
                    <div class="score-label">${a.status === 'done' ? verdictShort : a.status}</div>
                </div>
            </div>
            <div class="detail-meta">
                <h2>Analysis Report</h2>
                <div class="meta-grid">
                    <div class="meta-item">
                        <span class="meta-label">Analysis ID</span>
                        <span class="meta-value" style="font-family: monospace; font-size: 0.8rem;">${a.id.substring(0, 12)}…</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Status</span>
                        <span class="meta-value"><span class="status-badge ${a.status}">${a.status}</span></span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Source</span>
                        <span class="meta-value" style="text-transform: capitalize;">${a.source_type}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Media Type</span>
                        <span class="meta-value" style="text-transform: capitalize;">${a.media_type}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Submitted</span>
                        <span class="meta-value">${formatDate(a.created_at)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Completed</span>
                        <span class="meta-value">${a.completed_at ? formatDate(a.completed_at) : '—'}</span>
                    </div>
                    ${a.model_version ? `
                    <div class="meta-item">
                        <span class="meta-label">Engine</span>
                        <span class="meta-value">${a.model_version}</span>
                    </div>` : ''}
                    ${a.file_hash ? `
                    <div class="meta-item">
                        <span class="meta-label">File Hash</span>
                        <span class="meta-value" style="font-family: monospace; font-size: 0.75rem;">${a.file_hash.substring(0, 16)}…</span>
                    </div>` : ''}
                </div>
            </div>
        </div>

        ${a.status === 'done' && Object.keys(layers).length > 0 ? `
        <div class="result-summary-card glass-card">
            <div class="summary-grid">
                <div class="summary-stat">
                    <div class="summary-stat-icon" style="background: ${score > 0.5 ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)'}; color: ${scoreColor};">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    </div>
                    <div>
                        <div class="summary-stat-value" style="color: ${scoreColor};">${trustScore}%</div>
                        <div class="summary-stat-label">Trust Score</div>
                    </div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-icon" style="background: rgba(0,212,255,0.12); color: var(--accent-cyan);">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    </div>
                    <div>
                        <div class="summary-stat-value" style="color: var(--accent-cyan);">${confidence}%</div>
                        <div class="summary-stat-label">Confidence</div>
                    </div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-icon" style="background: rgba(124,58,237,0.12); color: var(--accent-purple);">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                    </div>
                    <div>
                        <div class="summary-stat-value" style="color: var(--accent-purple);">${Object.keys(layers).length}</div>
                        <div class="summary-stat-label">Layers Used</div>
                    </div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-icon" style="background: rgba(245,158,11,0.12); color: var(--accent-yellow);">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    </div>
                    <div>
                        <div class="summary-stat-value" style="color: var(--accent-yellow);">${framesAnalyzed || '1'}</div>
                        <div class="summary-stat-label">${framesAnalyzed ? 'Frames' : 'Image'} Analyzed</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="layers-card glass-card">
            <div class="layers-card-header">
                <h3>Forensic Layer Breakdown</h3>
                <span class="layers-subtitle">Each layer analyzes different aspects of the media</span>
            </div>
            ${layersHTML}
        </div>` : ''}

        ${a.status === 'failed' && a.error_message ? `
        <div class="error-card">
            <h3>Analysis Failed</h3>
            <p>${a.error_message}</p>
        </div>` : ''}

        ${a.status === 'queued' || a.status === 'processing' ? `
        <div class="processing-state glass-card">
            <div class="processing-animation">
                <div class="processing-ring"></div>
                <div class="processing-ring processing-ring-2"></div>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2" class="processing-icon">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
            </div>
            <h3 class="processing-title">Analyzing ${a.media_type === 'video' ? 'Video' : 'Image'}...</h3>
            <p class="processing-subtitle">Running forensic analysis across ${a.media_type === 'video' ? 'multiple frames' : 'all detection layers'}. This usually takes a few seconds.</p>
            <div class="processing-steps">
                <div class="processing-step ${a.status === 'processing' ? 'active' : 'done'}">
                    <div class="step-dot"></div>
                    <span>Upload verified</span>
                </div>
                <div class="processing-step ${a.status === 'processing' ? 'active' : ''}">
                    <div class="step-dot"></div>
                    <span>Running forensic analysis</span>
                </div>
                <div class="processing-step">
                    <div class="step-dot"></div>
                    <span>Generating report</span>
                </div>
            </div>
        </div>` : ''}
    `;

    // Animate the gauge fill and layer bars after a short delay
    if (a.status === 'done') {
        setTimeout(() => {
            const gaugeFill = container.querySelector('.gauge-fill');
            if (gaugeFill) gaugeFill.style.strokeDashoffset = offset;

            container.querySelectorAll('.layer-progress-fill').forEach(fill => {
                const targetWidth = fill.style.width;
                fill.style.width = '0%';
                requestAnimationFrame(() => {
                    fill.style.width = targetWidth;
                });
            });
        }, 50);
    }

    // Poll if still processing
    if (a.status === 'queued' || a.status === 'processing') {
        setTimeout(() => {
            if (state.currentPage === 'analysis') {
                loadAnalysisDetail(a.id);
            }
        }, 3000);
    }
}

// ═══════════════════════════════════════
// Utilities
// ═══════════════════════════════════════
function setLoading(btn, loading) {
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');
    if (loading) {
        if (text) text.classList.add('hidden');
        if (loader) loader.classList.remove('hidden');
        btn.disabled = true;
    } else {
        if (text) text.classList.remove('hidden');
        if (loader) loader.classList.add('hidden');
        btn.disabled = false;
    }
}

function toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);

    setTimeout(() => {
        el.classList.add('removing');
        setTimeout(() => el.remove(), 300);
    }, 4000);
}

function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    } catch {
        return isoStr;
    }
}

// ═══════════════════════════════════════
// Navigation Bindings
// ═══════════════════════════════════════
function initNavigation() {
    document.querySelectorAll('[data-navigate]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            navigate(el.dataset.navigate);
        });
    });
}

// ═══════════════════════════════════════
// Initialize
// ═══════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initAuth();
    initDashboard();
    updateNav();

    // Auto-navigate based on auth state
    if (state.token) {
        navigate('dashboard');
    } else {
        navigate('landing');
    }
});
