/* ── Finder App JS ── */
let currentSearchId = null;
let currentResults = null;

function notify(msg, type = 'info', duration = 4000) {
  const n = document.getElementById('notification');
  n.textContent = msg;
  n.className = `notification ${type}`;
  clearTimeout(n._timer);
  n._timer = setTimeout(() => n.classList.add('hidden'), duration);
}

function setTopic(topic) {
  document.getElementById('topicInput').value = topic;
}

// ── Search ─────────────────────────────────────────────────────
async function doSearch() {
  const topic = document.getElementById('topicInput').value.trim();
  if (!topic) { notify('Please enter a topic to research.', 'error'); return; }

  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Researching...';
  document.getElementById('loadingState').classList.remove('hidden');
  document.getElementById('resultsArea').classList.add('hidden');

  try {
    const r = await fetch('/finder/search', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ topic })
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Research failed.', 'error'); document.getElementById('loadingState').classList.add('hidden'); btn.disabled = false; btn.textContent = '🔍 Research Market'; return; }
    currentSearchId = d.search_id;
    currentResults = d.results;
    renderResults(d.results, topic);
    loadHistory();
    notify('Market research complete!', 'success');
  } catch(e) { notify('Error: ' + e.message, 'error'); }

  document.getElementById('loadingState').classList.add('hidden');
  btn.disabled = false;
  btn.textContent = '🔍 Research Market';
}

// Enter key support
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('topicInput');
  if (input) input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
  loadHistory();
});

// ── Render ─────────────────────────────────────────────────────
function renderResults(results, topic) {
  document.getElementById('topicDisplay').textContent = `Topic: "${topic}"`;
  const opp = results.overall_opportunity || 'MEDIUM';
  const badge = document.getElementById('opportunityBadge');
  badge.textContent = `Overall: ${opp} Opportunity`;
  badge.className = `opportunity-badge ${opp}`;
  document.getElementById('marketSummary').textContent = results.market_summary || '';

  // Niches
  const grid = document.getElementById('nichesGrid');
  grid.innerHTML = (results.niches || []).map((n, i) => `
    <div class="niche-card" style="animation-delay:${i*0.07}s">
      <div class="niche-header">
        <div class="niche-name">${escHtml(n.niche)}</div>
        <div>
          <div class="niche-score">${n.opportunity_score || '?'}</div>
          <span class="niche-score-label">/ 10</span>
        </div>
      </div>
      <div class="niche-desc">${escHtml(n.description||'')}</div>
      <div class="niche-meta">
        <span class="meta-tag meta-comp ${n.competition}">Comp: ${n.competition||'?'}</span>
        <span class="meta-tag meta-opp ${n.opportunity}">Opp: ${n.opportunity||'?'}</span>
        <span class="meta-tag meta-trend">${n.trend||'Stable'}</span>
      </div>
      <div class="niche-kws">${(n.keywords||[]).slice(0,6).map(k=>`<span class="niche-kw">${escHtml(k)}</span>`).join('')}</div>
      ${n.insider_tip ? `<div class="niche-tip">${escHtml(n.insider_tip)}</div>` : ''}
      <div style="margin-top:10px;font-size:.72rem;color:var(--muted)">${escHtml(n.price_range||'')} · ${escHtml(n.estimated_monthly_searches||'')} searches</div>
    </div>`).join('');

  // Keywords Table
  const tbody = document.getElementById('kwTableBody');
  tbody.innerHTML = (results.top_keywords || []).map(k => {
    const score = parseInt(k.opportunity_score) || 5;
    const pct = Math.min(100, score * 10);
    return `<tr>
      <td class="kw-word">${escHtml(k.keyword||'')}</td>
      <td>${escHtml(k.monthly_searches||'')}</td>
      <td><span class="comp-badge comp-${k.competition}">${k.competition||'?'}</span></td>
      <td>
        <div class="score-bar"><div class="score-fill" style="width:${pct}%"></div></div>
        ${score}/10
      </td>
      <td>${escHtml(k.avg_selling_price||'')}</td>
      <td style="font-size:.76rem;color:var(--muted)">${escHtml(k.suggested_use||'')}</td>
    </tr>`;
  }).join('');

  // Quick Wins
  const qwList = document.getElementById('quickWinsList');
  qwList.innerHTML = (results.quick_wins || []).map((w, i) => `
    <div class="qw-item">
      <div class="qw-num">${i+1}</div>
      <div>${escHtml(w)}</div>
    </div>`).join('');

  // Seasonal
  document.getElementById('seasonalText').textContent = results.seasonal_trends || '';

  // Avoid
  const avoidList = document.getElementById('avoidList');
  avoidList.innerHTML = (results.books_to_avoid || []).map(a => `
    <div class="avoid-item">${escHtml(a)}</div>`).join('');

  document.getElementById('resultsArea').classList.remove('hidden');
  document.getElementById('resultsArea').scrollIntoView({ behavior: 'smooth' });
}

// ── Export ─────────────────────────────────────────────────────
function exportResults() {
  if (!currentSearchId) { notify('No results to export.', 'error'); return; }
  notify('Preparing CSV...', 'info', 2000);
  window.location.href = `/finder/export/${currentSearchId}`;
}

function resetSearch() {
  currentSearchId = null; currentResults = null;
  document.getElementById('resultsArea').classList.add('hidden');
  document.getElementById('topicInput').value = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── History ─────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const r = await fetch('/finder/history');
    const rows = await r.json();
    const list = document.getElementById('historyList');
    if (!rows.length) { list.innerHTML = '<p class="empty-state">No searches yet.</p>'; return; }
    list.innerHTML = rows.map(row => `
      <div class="history-item" onclick="loadResult('${row.id}')">
        <strong>${escHtml(row.seed_topic)}</strong>
        <span class="history-date">${(row.created_at||'').slice(0,10)}</span>
      </div>`).join('');
  } catch(e) {}
}

async function loadResult(id) {
  try {
    const r = await fetch(`/finder/result/${id}`);
    const d = await r.json();
    if (!r.ok) { notify('Could not load result.', 'error'); return; }
    currentSearchId = id;
    currentResults = d.results;
    renderResults(d.results, d.topic);
    notify('Loaded previous research.', 'info');
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
    const r = await fetch('/finder/reports/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: currentSearchId || '', reason, description })
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
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/finder/sw.js');
