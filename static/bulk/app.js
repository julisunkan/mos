/* ── Bulk App JS ── */
let currentBatchId = null;
let currentBooks = [];
let editingBookId = null;

function notify(msg, type = 'info', duration = 4000) {
  const n = document.getElementById('notification');
  n.textContent = msg;
  n.className = `notification ${type}`;
  clearTimeout(n._timer);
  n._timer = setTimeout(() => n.classList.add('hidden'), duration);
}

function adjustCount(delta) {
  const input = document.getElementById('bookCount');
  const val = Math.max(1, Math.min(50, parseInt(input.value || 5) + delta));
  input.value = val;
  updateGenerateBtn();
}

function updateGenerateBtn() {
  const count = parseInt(document.getElementById('bookCount').value) || 5;
  document.getElementById('generateBtn').innerHTML = `⚡ Generate ${count} Books`;
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('bookCount').addEventListener('input', updateGenerateBtn);
  updateGenerateBtn();
});

// ── Generate Batch ─────────────────────────────────────────────
async function generateBatch() {
  const niche = document.getElementById('nicheInput').value.trim();
  if (!niche) { notify('Please enter a niche or topic.', 'error'); return; }
  const count = Math.max(1, Math.min(50, parseInt(document.getElementById('bookCount').value) || 5));
  const batchName = document.getElementById('batchName').value.trim();
  const extraNotes = document.getElementById('extraNotes').value.trim();

  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Generating...';
  document.getElementById('loadingState').classList.remove('hidden');
  document.getElementById('batchResults').classList.add('hidden');

  try {
    const r = await fetch('/bulk/generate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ niche, count, batch_name: batchName, extra_notes: extraNotes })
    });
    const d = await r.json();
    if (!r.ok) { notify(d.error || 'Generation failed.', 'error'); document.getElementById('loadingState').classList.add('hidden'); btn.disabled = false; updateGenerateBtn(); return; }
    currentBatchId = d.batch_id;
    currentBooks = d.books;
    renderBooks(d.books, niche, count);
    loadBatchesList();
    notify(`${d.count} books generated!`, 'success');
  } catch(e) { notify('Error: ' + e.message, 'error'); }

  document.getElementById('loadingState').classList.add('hidden');
  btn.disabled = false;
  updateGenerateBtn();
}

// ── Render Books ───────────────────────────────────────────────
function renderBooks(books, niche, count) {
  document.getElementById('batchMeta').textContent = `${books.length} books · Niche: ${niche}`;
  document.getElementById('exportBtn').onclick = () => exportCSV();

  const tbody = document.getElementById('booksTableBody');
  tbody.innerHTML = books.map((book, i) => {
    const kws = Array.isArray(book.keywords) ? book.keywords : (book.keywords || '').split(',').map(k=>k.trim());
    return `<tr data-idx="${i}">
      <td>${i+1}</td>
      <td title="${escHtml(book.title || '')}">${escHtml((book.title||'').slice(0,50))}${(book.title||'').length > 50 ? '…' : ''}</td>
      <td title="${escHtml(book.subtitle || '')}">${escHtml((book.subtitle||'').slice(0,40))}${(book.subtitle||'').length > 40 ? '…' : ''}</td>
      <td><div class="kw-pills">${kws.slice(0,3).map(k=>`<span class="kw-pill">${escHtml(k)}</span>`).join('')}${kws.length>3?`<span class="kw-pill">+${kws.length-3}</span>`:''}</div></td>
      <td title="${escHtml(book.primary_category||'')}">${escHtml((book.primary_category||'').slice(0,35))}…</td>
      <td>${book.pages||120}</td>
      <td><button class="btn-edit-row" onclick="openEdit('${currentBatchId}',${i})">✏ Edit</button></td>
    </tr>`;
  }).join('');

  document.getElementById('batchResults').classList.remove('hidden');
  document.getElementById('batchResults').scrollIntoView({ behavior: 'smooth' });
}

// ── Edit Drawer ────────────────────────────────────────────────
async function openEdit(batchId, idx) {
  const book = currentBooks[idx];
  if (!book) return;
  editingBookId = book.id;
  document.getElementById('editTitle').value      = book.title || '';
  document.getElementById('editSubtitle').value   = book.subtitle || '';
  document.getElementById('editDesc').value       = book.description || '';
  const kws = Array.isArray(book.keywords) ? book.keywords.join(', ') : (book.keywords || '');
  document.getElementById('editKeywords').value   = kws;
  document.getElementById('editPrimary').value    = book.primary_category || '';
  document.getElementById('editSecondary').value  = book.secondary_category || '';
  document.getElementById('editPages').value      = book.pages || 120;
  const langSel = document.getElementById('editLanguage');
  for (let opt of langSel.options) if (opt.value === book.language) { opt.selected = true; break; }
  document.getElementById('editDrawer').classList.remove('hidden');
}

function closeDrawer() {
  document.getElementById('editDrawer').classList.add('hidden');
  editingBookId = null;
}

async function saveBook() {
  if (!editingBookId) return;
  const kws = document.getElementById('editKeywords').value.split(',').map(k=>k.trim()).filter(Boolean);
  const data = {
    title:              document.getElementById('editTitle').value,
    subtitle:           document.getElementById('editSubtitle').value,
    description:        document.getElementById('editDesc').value,
    keywords:           kws,
    primary_category:   document.getElementById('editPrimary').value,
    secondary_category: document.getElementById('editSecondary').value,
    pages:              parseInt(document.getElementById('editPages').value)||120,
    language:           document.getElementById('editLanguage').value,
  };
  try {
    const r = await fetch(`/bulk/update-book/${editingBookId}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(data)
    });
    const d = await r.json();
    if (!r.ok) { notify('Save failed: ' + (d.error||''), 'error'); return; }
    // Update local data
    const idx = currentBooks.findIndex(b => b.id === editingBookId);
    if (idx >= 0) currentBooks[idx] = { ...currentBooks[idx], ...data };
    closeDrawer();
    notify('Book updated!', 'success');
    // Re-render table row
    const niche = document.getElementById('nicheInput').value.trim() || '';
    renderBooks(currentBooks, niche, currentBooks.length);
  } catch(e) { notify('Error: ' + e.message, 'error'); }
}

// ── Export ─────────────────────────────────────────────────────
function exportCSV() {
  if (!currentBatchId) { notify('No batch to export.', 'error'); return; }
  notify('Preparing CSV...', 'info', 2000);
  window.location.href = `/bulk/export-csv/${currentBatchId}`;
}

function resetBatch() {
  currentBatchId = null; currentBooks = [];
  document.getElementById('batchResults').classList.add('hidden');
  document.getElementById('nicheInput').value = '';
  document.getElementById('batchName').value = '';
  document.getElementById('extraNotes').value = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Load Batch ─────────────────────────────────────────────────
async function loadBatch(batchId) {
  try {
    const r = await fetch(`/bulk/batch/${batchId}`);
    const d = await r.json();
    if (!r.ok) { notify('Could not load batch.', 'error'); return; }
    currentBatchId = batchId;
    currentBooks = d.books;
    renderBooks(d.books, d.batch.niche, d.books.length);
    notify(`Loaded batch: ${d.batch.name}`, 'info');
  } catch(e) { notify('Error loading batch.', 'error'); }
}

// ── Batches List ───────────────────────────────────────────────
async function loadBatchesList() {
  try {
    const r = await fetch('/bulk/batches');
    const rows = await r.json();
    const list = document.getElementById('batchesList');
    if (!rows.length) { list.innerHTML = '<p class="empty-state">No batches created yet.</p>'; return; }
    list.innerHTML = rows.map(b => `
      <div class="history-item" onclick="loadBatch('${b.id}')">
        <div>
          <strong>${escHtml(b.name||b.niche)}</strong>
          <span class="history-meta">${b.book_count} books · ${escHtml(b.niche||'')}</span>
        </div>
        <span class="history-date">${(b.created_at||'').slice(0,10)}</span>
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
    const r = await fetch('/bulk/reports/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: currentBatchId || '', reason, description })
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

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/bulk/sw.js');
document.addEventListener('DOMContentLoaded', loadBatchesList);
