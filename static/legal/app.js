/* ── Legal App JS ── */
let currentDocId = null;
let currentAnalysis = null;

// ── Notifications ─────────────────────────────────────────────
function notify(msg, type = 'info', duration = 4000) {
  const n = document.getElementById('notification');
  n.textContent = msg;
  n.className = `notification ${type}`;
  clearTimeout(n._timer);
  n._timer = setTimeout(() => n.classList.add('hidden'), duration);
}

// ── Drop Zone ─────────────────────────────────────────────────
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) handleFile(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

function handleFile(file) {
  const allowed = ['pdf','docx','doc','txt'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) { notify('Please upload a PDF, DOCX, DOC or TXT file.', 'error'); return; }
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileInfo').classList.remove('hidden');
  uploadFile(file);
}

function removeFile() {
  document.getElementById('fileInfo').classList.add('hidden');
  document.getElementById('fileName').textContent = '';
  currentDocId = null;
  fileInput.value = '';
  document.getElementById('analyzeBtn').disabled = false;
  document.getElementById('analyzeBtn').textContent = '🔍 Analyze for Risks';
}

// ── Upload ─────────────────────────────────────────────────────
async function uploadFile(file) {
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.textContent = 'Uploading...';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch('/legal/upload', { method: 'POST', body: fd });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Upload failed.', 'error'); btn.disabled = false; btn.innerHTML = '<span class="btn-icon">🔍</span> Analyze for Risks'; return; }
    currentDocId = d.doc_id;
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🔍</span> Analyze for Risks';
    notify('Document uploaded. Click "Analyze for Risks" to proceed.', 'success');
  } catch(e) {
    notify('Upload error: ' + e.message, 'error');
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🔍</span> Analyze for Risks';
  }
}

// ── Analyze ────────────────────────────────────────────────────
async function analyzeDocument() {
  if (!currentDocId) { notify('Please upload a document first.', 'error'); return; }
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.textContent = 'Analyzing...';
  document.getElementById('loadingState').classList.remove('hidden');
  document.getElementById('resultsSection').classList.add('hidden');
  try {
    const r = await fetch(`/legal/analyze/${currentDocId}`, { method: 'POST' });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Analysis failed.', 'error'); document.getElementById('loadingState').classList.add('hidden'); btn.disabled = false; btn.innerHTML = '<span class="btn-icon">🔍</span> Analyze for Risks'; return; }
    currentAnalysis = d;
    renderResults(d.result);
    loadHistory();
    notify('Analysis complete!', 'success');
  } catch(e) {
    notify('Analysis error: ' + e.message, 'error');
  }
  document.getElementById('loadingState').classList.add('hidden');
  btn.disabled = false;
  btn.innerHTML = '<span class="btn-icon">🔍</span> Analyze for Risks';
}

// ── Render Results ─────────────────────────────────────────────
function renderResults(result) {
  const section = document.getElementById('resultsSection');
  const overall = result.overall_risk || 'UNKNOWN';
  const badge = document.getElementById('overallRiskBadge');
  badge.textContent = `● ${overall} RISK`;
  badge.className = `risk-badge ${overall}`;

  const doc = document.getElementById('uploadSection').querySelector('#fileName').textContent;
  document.getElementById('docNameDisplay').textContent = `📄 ${doc}`;
  document.getElementById('clauseCountDisplay').textContent = `${result.clauses?.length || 0} clauses flagged`;
  document.getElementById('summaryText').textContent = result.summary || '';

  const list = document.getElementById('clausesList');
  list.innerHTML = '';
  (result.clauses || []).forEach((clause, i) => {
    const card = document.createElement('div');
    card.className = `clause-card ${clause.risk_level || 'MEDIUM'}`;
    card.style.animationDelay = `${i * 0.06}s`;
    card.innerHTML = `
      <div class="clause-header">
        <span class="clause-risk risk-${clause.risk_level}">${clause.risk_level}</span>
        <span class="clause-type">${clause.risk_type || ''}</span>
        <span class="clause-num">#${i+1}</span>
      </div>
      <div class="clause-text">${escHtml(clause.clause_text || '')}</div>
      <div class="clause-explanation">${escHtml(clause.explanation || '')}</div>
      <div class="clause-rec">${escHtml(clause.recommendation || '')}</div>`;
    list.appendChild(card);
  });

  section.classList.remove('hidden');
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Download Report ────────────────────────────────────────────
function downloadReport() {
  if (!currentDocId) { notify('No document to download report for.', 'error'); return; }
  notify('Preparing PDF report…', 'info');
  const a = document.createElement('a');
  a.href = `/legal/report/${currentDocId}`;
  a.download = `risk_report_${currentDocId.slice(0,8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function resetAnalysis() {
  removeFile();
  document.getElementById('resultsSection').classList.add('hidden');
  document.getElementById('loadingState').classList.add('hidden');
  document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}

// ── History ─────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const r = await fetch('/legal/history');
    const rows = await r.json();
    const list = document.getElementById('historyList');
    if (!rows.length) { list.innerHTML = '<p class="empty-state">No documents analyzed yet.</p>'; return; }
    list.innerHTML = rows.map(row => {
      const risk = row.overall_risk || '—';
      const rClass = ['HIGH','MEDIUM','LOW'].includes(risk) ? risk : '';
      const hasReport = row.status === 'analysed' && row.overall_risk;
      return `<div class="history-item">
        <div style="flex:1">
          <strong>${escHtml(row.original_name || 'Document')}</strong>
          <div class="history-meta">
            <span class="history-risk risk-${rClass}">${risk !== '—' ? risk + ' RISK' : 'Not analyzed'}</span>
            <span>${row.file_type?.toUpperCase() || ''}</span>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          ${hasReport ? `<button class="btn-dl-history" onclick="downloadHistoryReport('${row.id}')">⬇ PDF</button>` : ''}
          <span class="history-date">${(row.created_at || '').slice(0,10)}</span>
        </div>
      </div>`;
    }).join('');
  } catch(e) { console.error(e); }
}

function downloadHistoryReport(id) {
  notify('Preparing PDF report…', 'info');
  const a = document.createElement('a');
  a.href = `/legal/report/${id}`;
  a.download = `risk_report_${id.slice(0,8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ── Report This Content ─────────────────────────────────────────
function toggleReportForm() {
  const wrap = document.getElementById('reportFormWrap');
  wrap.classList.toggle('hidden');
  if (!wrap.classList.contains('hidden')) {
    document.getElementById('reportReason').value = '';
    document.getElementById('reportDesc').value = '';
  }
}

async function submitReport() {
  const reason = document.getElementById('reportReason').value.trim();
  const description = document.getElementById('reportDesc').value.trim();
  if (!reason) { notify('Please select a reason before submitting.', 'error'); return; }
  const btn = document.querySelector('.btn-submit-report');
  btn.disabled = true;
  btn.textContent = 'Submitting…';
  try {
    const r = await fetch('/legal/reports/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: currentDocId || '', reason, description })
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Failed to submit report.', 'error'); }
    else {
      notify('Report submitted. Thank you for your feedback.', 'success');
      document.getElementById('reportFormWrap').classList.add('hidden');
    }
  } catch(e) {
    notify('Error submitting report: ' + e.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = 'Submit Report';
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── PWA ────────────────────────────────────────────────────────
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/legal/sw.js');

// ── Init ───────────────────────────────────────────────────────
loadHistory();
