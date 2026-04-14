/* ── Optimizer App JS ── */
let currentProjectId = null;
let currentResult = null;

function notify(msg, type = 'info', duration = 4000) {
  const n = document.getElementById('notification');
  n.textContent = msg;
  n.className = `notification ${type}`;
  clearTimeout(n._timer);
  n._timer = setTimeout(() => n.classList.add('hidden'), duration);
}

// ── Optimize ───────────────────────────────────────────────────
async function optimizeMetadata() {
  const genre       = document.getElementById('genreSelect').value;
  const audience    = document.getElementById('audience').value.trim();
  const roughTitle  = document.getElementById('roughTitle').value.trim();
  const rawKeywords = document.getElementById('rawKeywords').value.trim();
  const descHint    = document.getElementById('descHint').value.trim();

  if (!genre) { notify('Please select a genre/category.', 'error'); return; }
  if (!roughTitle) { notify('Please enter a rough title idea.', 'error'); return; }

  const btn = document.getElementById('optimizeBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Optimizing...';
  document.getElementById('loadingState').classList.remove('hidden');
  document.getElementById('resultsArea').classList.add('hidden');

  try {
    const r = await fetch('/optimizer/optimize', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ genre, audience, rough_title: roughTitle, keywords: rawKeywords, description_hint: descHint })
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Optimization failed.', 'error'); document.getElementById('loadingState').classList.add('hidden'); btn.disabled = false; btn.textContent = '🚀 Optimize My Metadata'; return; }
    currentProjectId = d.project_id;
    currentResult = d.result;
    renderResults(d.result);
    loadHistory();
    notify('Metadata optimized successfully!', 'success');
  } catch(e) { notify('Error: ' + e.message, 'error'); }

  document.getElementById('loadingState').classList.add('hidden');
  btn.disabled = false;
  btn.textContent = '🚀 Optimize My Metadata';
}

// ── Render ─────────────────────────────────────────────────────
function renderResults(result) {
  // Titles
  const tl = document.getElementById('titlesList');
  tl.innerHTML = (result.titles || []).map((t, i) => `
    <div class="title-option">
      <div class="title-option-num">Option ${i+1}</div>
      <div class="title-option-title">${escHtml(t.title)}</div>
      <div class="title-option-sub">${escHtml(t.subtitle || '')}</div>
      <div class="title-option-reason">${escHtml(t.reason || '')}</div>
      <button class="copy-btn" onclick="copyText('${escAttr(t.title + (t.subtitle ? ': '+t.subtitle : ''))}')">📋</button>
    </div>`).join('');

  // Description
  const desc = result.description || {};
  document.getElementById('descHook').textContent = desc.hook || '';
  document.getElementById('descBody').innerHTML = desc.body || '';
  document.getElementById('descCta').textContent = desc.cta || '';

  // Keywords
  const kl = document.getElementById('keywordsList');
  kl.innerHTML = (result.keywords || []).map((kw, i) => `
    <div class="kw-tag" title="Click to copy" onclick="copyText('${escAttr(kw)}')">${i+1}. ${escHtml(kw)}</div>`).join('');

  // Categories
  const cl = document.getElementById('categoriesList');
  cl.innerHTML = (result.categories || []).map(cat => `
    <div class="category-item">
      <div>
        <div class="cat-path">${escHtml(cat.primary || '')}</div>
        <div class="cat-reason">${escHtml(cat.reason || '')}</div>
      </div>
    </div>`).join('');

  // Bullets
  const bl = document.getElementById('bulletsList');
  bl.innerHTML = (result.a_plus_bullets || []).map(b => `
    <div class="bullet-item"><span class="bullet-dot">★</span><span>${escHtml(b)}</span></div>`).join('');

  // Tips
  const tipsList = document.getElementById('tipsList');
  tipsList.innerHTML = (result.seo_tips || []).map((tip, i) => `
    <div class="tip-item"><span class="tip-num">${i+1}.</span><span>${escHtml(tip)}</span></div>`).join('');

  document.getElementById('resultsArea').classList.remove('hidden');
  document.getElementById('resultsArea').scrollIntoView({ behavior: 'smooth' });
}

// ── Copy Helpers ───────────────────────────────────────────────
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); notify('Copied!', 'success', 1500); }
  catch(e) { notify('Copy failed', 'error'); }
}

function copyDesc() {
  if (!currentResult) return;
  const d = currentResult.description || {};
  const text = [d.hook, d.body?.replace(/<[^>]+>/g,''), d.cta].filter(Boolean).join('\n\n');
  copyText(text);
}

function copyKeywords() {
  if (!currentResult) return;
  copyText((currentResult.keywords || []).join(', '));
}

function copyBullets() {
  if (!currentResult) return;
  copyText((currentResult.a_plus_bullets || []).map(b => '• ' + b).join('\n'));
}

function copyAll() {
  if (!currentResult) return;
  const r = currentResult;
  const parts = [
    '=== TITLES ===',
    (r.titles||[]).map((t,i)=>`${i+1}. ${t.title}: ${t.subtitle}`).join('\n'),
    '\n=== DESCRIPTION ===',
    r.description?.hook || '',
    r.description?.body?.replace(/<[^>]+>/g,'') || '',
    r.description?.cta || '',
    '\n=== KEYWORDS ===',
    (r.keywords||[]).join(', '),
    '\n=== CATEGORIES ===',
    (r.categories||[]).map(c=>c.primary).join('\n'),
    '\n=== A+ BULLETS ===',
    (r.a_plus_bullets||[]).map(b=>'• '+b).join('\n'),
  ];
  copyText(parts.join('\n'));
}

async function exportResults() {
  if (!currentProjectId) { notify('No results to export.', 'error'); return; }
  notify('Downloading...', 'info', 2000);
  window.location.href = `/optimizer/export/${currentProjectId}`;
}

function resetForm() {
  currentProjectId = null; currentResult = null;
  document.getElementById('resultsArea').classList.add('hidden');
  document.getElementById('roughTitle').value = '';
  document.getElementById('rawKeywords').value = '';
  document.getElementById('descHint').value = '';
  document.getElementById('audience').value = '';
  document.getElementById('genreSelect').value = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── History ────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const r = await fetch('/optimizer/history');
    const rows = await r.json();
    const list = document.getElementById('historyList');
    if (!rows.length) { list.innerHTML = '<p class="empty-state">No optimizations yet.</p>'; return; }
    list.innerHTML = rows.map(row => `
      <div class="history-item" onclick="loadHistResult('${row.id}')">
        <div>
          <strong>${escHtml(row.rough_title || 'Untitled')}</strong>
          <span style="color:var(--muted);font-size:.78rem;margin-left:8px">${escHtml(row.genre || '')}</span>
        </div>
        <span class="history-date">${(row.created_at||'').slice(0,10)}</span>
      </div>`).join('');
  } catch(e) {}
}

async function loadHistResult(id) {
  try {
    const r = await fetch(`/optimizer/result/${id}`);
    const d = await r.json();
    if (!r.ok) { notify('Could not load result.', 'error'); return; }
    currentProjectId = id;
    currentResult = d.result;
    renderResults(d.result);
    notify('Loaded previous optimization.', 'info');
  } catch(e) { notify('Error loading result.', 'error'); }
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
    const r = await fetch('/optimizer/reports/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: currentProjectId || '', reason, description })
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
function escAttr(s) {
  return String(s).replace(/'/g,"\\'").replace(/"/g,'&quot;');
}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/optimizer/sw.js');
document.addEventListener('DOMContentLoaded', loadHistory);
