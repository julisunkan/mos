/* ── Gen App JS ── */
let currentType = 'interior';
let selectedTemplate = null;
let selectedCoverTpl = null;
let currentProjectId = null;

function notify(msg, type = 'info', duration = 4000) {
  const n = document.getElementById('notification');
  n.textContent = msg;
  n.className = `notification ${type}`;
  clearTimeout(n._timer);
  n._timer = setTimeout(() => n.classList.add('hidden'), duration);
}

function setType(type) {
  currentType = type;
  document.getElementById('interiorPanel').classList.toggle('hidden', type !== 'interior');
  document.getElementById('coverPanel').classList.toggle('hidden', type !== 'cover');
  document.getElementById('btnInterior').classList.toggle('active', type === 'interior');
  document.getElementById('btnCover').classList.toggle('active', type === 'cover');
}

function selectTemplate(id, el) {
  document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  selectedTemplate = id;
}

function selectCoverTemplate(id, el) {
  document.querySelectorAll('.cover-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  selectedCoverTpl = id;
}

// ── AI Enhance ────────────────────────────────────────────────
async function enhancePrompt() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) { notify('Enter a prompt first to enhance.', 'error'); return; }
  notify('Enhancing prompt with AI...', 'info', 30000);
  try {
    const r = await fetch('/gen/enhance-prompt', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ prompt, type: currentType })
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Enhancement failed.', 'error'); return; }
    document.getElementById('promptInput').value = d.enhanced_prompt || prompt;
    showSuggestions(d);
    notify('Prompt enhanced!', 'success');
  } catch(e) { notify('Error: ' + e.message, 'error'); }
}

async function enhanceCoverPrompt() {
  const prompt = document.getElementById('coverPrompt').value.trim();
  const title = document.getElementById('coverTitle').value.trim();
  if (!prompt && !title) { notify('Enter a title or prompt first.', 'error'); return; }
  notify('Enhancing with AI...', 'info', 30000);
  try {
    const r = await fetch('/gen/enhance-prompt', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ prompt: prompt || title, type: 'cover' })
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Enhancement failed.', 'error'); return; }
    if (d.suggested_title && !document.getElementById('coverTitle').value)
      document.getElementById('coverTitle').value = d.suggested_title;
    if (d.suggested_subtitle && !document.getElementById('coverSubtitle').value)
      document.getElementById('coverSubtitle').value = d.suggested_subtitle;
    document.getElementById('coverPrompt').value = d.enhanced_prompt || prompt;
    showSuggestions(d);
    notify('Cover details enhanced!', 'success');
  } catch(e) { notify('Error: ' + e.message, 'error'); }
}

function showSuggestions(d) {
  const panel = document.getElementById('suggestionsPanel');
  const content = document.getElementById('suggestionsContent');
  let html = '';
  if (d.suggested_title) html += `<div class="suggestion-item"><div class="suggestion-label">Suggested Title</div>${escHtml(d.suggested_title)}</div>`;
  if (d.suggested_subtitle) html += `<div class="suggestion-item"><div class="suggestion-label">Suggested Subtitle</div>${escHtml(d.suggested_subtitle)}</div>`;
  if (d.target_audience) html += `<div class="suggestion-item"><div class="suggestion-label">Target Audience</div>${escHtml(d.target_audience)}</div>`;
  if (d.tips?.length) html += `<div class="suggestion-item"><div class="suggestion-label">Tips</div>${d.tips.map(t=>`<div>• ${escHtml(t)}</div>`).join('')}</div>`;
  content.innerHTML = html;
  panel.classList.toggle('hidden', !html);
}

// ── Generate PDF ───────────────────────────────────────────────
async function generatePDF() {
  const btn = document.getElementById('generateBtn');
  let body = {};

  if (currentType === 'interior') {
    if (!selectedTemplate) { notify('Please select an interior template.', 'error'); return; }
    body = {
      type: 'interior',
      template_id: selectedTemplate,
      paper_size: document.getElementById('paperSize').value,
      page_count: parseInt(document.getElementById('pageCount').value) || 120,
      prompt: document.getElementById('promptInput').value,
      title: 'KDP Interior'
    };
  } else {
    const title = document.getElementById('coverTitle').value.trim();
    if (!title) { notify('Please enter a book title.', 'error'); return; }
    if (!selectedCoverTpl) { notify('Please select a cover template.', 'error'); return; }
    body = {
      type: 'cover',
      template_id: selectedCoverTpl,
      title,
      subtitle: document.getElementById('coverSubtitle').value,
      author: document.getElementById('coverAuthor').value,
      prompt: document.getElementById('coverPrompt').value
    };
  }

  btn.disabled = true;
  document.getElementById('loadingState').classList.remove('hidden');
  document.getElementById('resultCard').classList.add('hidden');

  try {
    const r = await fetch('/gen/generate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Generation failed.', 'error'); document.getElementById('loadingState').classList.add('hidden'); btn.disabled = false; return; }
    currentProjectId = d.project_id;
    const typeLabel = currentType === 'interior' ? 'Interior PDF' : 'Cover PDF';
    document.getElementById('resultDesc').textContent =
      currentType === 'interior'
        ? `${body.page_count}-page ${body.paper_size} interior using "${selectedTemplate}" template`
        : `Cover for "${body.title}" using ${selectedCoverTpl} template`;
    document.getElementById('downloadBtn').onclick = () => downloadProject();
    document.getElementById('resultCard').classList.remove('hidden');
    loadHistory();
    notify(`${typeLabel} generated successfully!`, 'success');
  } catch(e) { notify('Error: ' + e.message, 'error'); }

  document.getElementById('loadingState').classList.add('hidden');
  btn.disabled = false;
  document.getElementById('resultCard').scrollIntoView({ behavior: 'smooth' });
}

function downloadProject() {
  if (!currentProjectId) return;
  notify('Downloading...', 'info', 2000);
  window.location.href = `/gen/download/${currentProjectId}`;
}

function resetGen() {
  currentProjectId = null;
  document.getElementById('resultCard').classList.add('hidden');
  document.getElementById('suggestionsPanel').classList.add('hidden');
  document.querySelectorAll('.template-card, .cover-card').forEach(c => c.classList.remove('selected'));
  selectedTemplate = null; selectedCoverTpl = null;
  document.getElementById('promptInput').value = '';
  document.getElementById('generateBtn').scrollIntoView({ behavior: 'smooth' });
}

// ── History ─────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const r = await fetch('/gen/history');
    const rows = await r.json();
    const list = document.getElementById('historyList');
    if (!rows.length) { list.innerHTML = '<p class="empty-state">No generations yet.</p>'; return; }
    list.innerHTML = rows.map(row => `
      <div class="history-item" onclick="window.location='/gen/download/${row.id}'">
        <div>
          <strong>${escHtml(row.title || 'Untitled')}</strong>
          <span class="history-meta"> · ${row.project_type} · ${row.template_id} · ${row.page_count||''} pages</span>
        </div>
        <span class="history-date">${(row.created_at||'').slice(0,10)}</span>
      </div>`).join('');
  } catch(e) {}
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
    const r = await fetch('/gen/reports/submit', {
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

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/gen/sw.js');

// Auto-select first template
document.addEventListener('DOMContentLoaded', () => {
  const first = document.querySelector('.template-card');
  if (first) { first.click(); }
  const firstCover = document.querySelector('.cover-card');
  if (firstCover) firstCover.click();
  loadHistory();
});
