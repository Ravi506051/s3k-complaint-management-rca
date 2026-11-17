const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
let state = { complaints: [], audit: [], metrics: {} };
let selectedId = null;

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function toast(message, bad = false) {
  const box = $('#toast');
  box.textContent = message;
  box.style.background = bad ? '#873f31' : '#173d3c';
  box.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => box.classList.remove('show'), 3600);
}

function date(value) { return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
function statusClass(value) { return value.toLowerCase().replaceAll(' ', '-'); }

function renderRows() {
  const query = $('#search').value.trim().toLowerCase();
  const status = $('#status-filter').value;
  const rows = state.complaints.filter(item => (!status || item.status === status) &&
    (!query || `${item.id} cc-${String(item.id).padStart(3,'0')} ${item.customer} ${item.batch} ${item.category}`.toLowerCase().includes(query)));
  $('#results-count').textContent = `${rows.length} of ${state.complaints.length} cases`;
  $('#case-rows').innerHTML = rows.length ? rows.map(item => `<tr data-id="${item.id}" tabindex="0" aria-label="Open complaint CC-${String(item.id).padStart(3,'0')}">
    <td><div class="case-id">CC-${String(item.id).padStart(3,'0')} · ${escapeHtml(item.batch)}</div><div class="case-customer">${escapeHtml(item.customer)}</div></td>
    <td>${escapeHtml(item.category)}</td><td><span class="tag ${escapeHtml(item.priority.toLowerCase())}">${escapeHtml(item.priority)}</span></td>
    <td>${escapeHtml(item.owner || 'Unassigned')}</td><td class="${item.overdue ? 'overdue' : ''}">${date(item.due_at)}${item.overdue ? ' · Late' : ''}</td>
    <td><span class="status ${statusClass(item.status)}">${escapeHtml(item.status)}</span></td><td class="row-arrow">↗</td></tr>`).join('')
    : '<tr><td colspan="7" class="empty">No cases match this view.</td></tr>';
}

function renderActivity() {
  const labels = { captured: 'Complaint captured', human_assignment: 'Owner assigned', rca_capa_submitted: 'RCA & CAPA submitted', human_approved: 'Resolution approved' };
  $('#activity-list').innerHTML = state.audit.slice(0, 5).map(entry => `<div class="activity-item"><span class="activity-icon">✓</span><div><strong>${escapeHtml(labels[entry.action] || entry.action)} · CC-${String(entry.complaint_id).padStart(3,'0')}</strong><p>${escapeHtml(entry.actor)} · ${date(entry.at)}</p></div></div>`).join('') || '<p class="empty">No activity yet.</p>';
}

async function refresh() {
  state = await api('/api/state');
  for (const key of ['open','overdue','unassigned','resolved']) $(`#metric-${key}`).textContent = state.metrics[key];
  $('#nav-count').textContent = state.metrics.open;
  renderRows(); renderActivity();
}

function option(value, selected) { return `<option${value === selected ? ' selected' : ''}>${escapeHtml(value)}</option>`; }

async function openCase(id) {
  selectedId = Number(id);
  const item = state.complaints.find(caseItem => caseItem.id === selectedId);
  if (!item) return;
  const advice = await api(`/api/complaints/${id}/suggestion`);
  $('#dialog-title').textContent = `CC-${String(id).padStart(3,'0')} · ${item.customer}`;
  $('#case-detail').innerHTML = `<div class="detail-summary"><span class="kicker">CUSTOMER REPORT · ${escapeHtml(item.channel)}</span><p>${escapeHtml(item.description)}</p></div>
    <div class="detail-meta"><div><small>Batch / reference</small><strong>${escapeHtml(item.batch)}</strong></div><div><small>Current status</small><strong>${escapeHtml(item.status)}</strong></div><div><small>Target date</small><strong>${date(item.due_at)}${item.overdue ? ' · Overdue' : ''}</strong></div><div><small>Owner</small><strong>${escapeHtml(item.owner || 'Not assigned')}</strong></div></div>
    <div class="suggestion"><strong>✳ Reviewable triage suggestion</strong><p>${escapeHtml(advice.category)} · ${escapeHtml(advice.priority)} priority · Suggested owner: ${escapeHtml(advice.suggested_owner)}</p><small>${advice.similar_cases.length ? `Same-batch cases: ${advice.similar_cases.map(c => `CC-${String(c.id).padStart(3,'0')}`).join(', ')}. Review before treating as duplicates.` : 'No same-batch cases found.'} ${escapeHtml(advice.disclaimer)}</small></div>
    ${item.status === 'Resolved' ? `<div class="form-section"><h3>Approved outcome</h3><p class="form-note">RCA: ${escapeHtml(item.rca)}<br>CAPA: ${escapeHtml(item.capa)}<br>Resolution: ${escapeHtml(item.resolution)}<br>Approved by: ${escapeHtml(item.approved_by)}</p></div>` : `
    <form id="assign-form" class="form-section"><h3>1. Human review & assignment</h3><div class="form-grid"><label>Owner<select name="owner" required>${['Quality','Production','Logistics','Customer Service'].map(v => option(v,item.owner)).join('')}</select></label><label>Priority<select name="priority" required>${['Low','Medium','High','Critical'].map(v => option(v,item.priority)).join('')}</select></label></div><label>Category<input name="category" required maxlength="80" value="${escapeHtml(item.category)}"></label><label>Reviewed by<input name="actor" required value="Demo service lead"></label><button class="button light wide" type="submit">Confirm owner & classification →</button></form>
    <form id="rca-form" class="form-section"><h3>2. Root cause & corrective action</h3><label>Root cause analysis<textarea name="rca" required minlength="15" placeholder="Evidence-backed cause, not just a symptom">${escapeHtml(item.rca)}</textarea></label><label>Corrective / preventive action<textarea name="capa" required minlength="15" placeholder="Owner, action and prevention plan">${escapeHtml(item.capa)}</textarea></label><label>Recorded by<input name="actor" required value="Demo quality lead"></label><button class="button light wide" type="submit">Submit RCA / CAPA for approval →</button></form>
    <form id="approve-form" class="form-section"><h3>3. Approve resolution</h3><label>Customer-ready resolution<textarea name="resolution" required minlength="15" placeholder="Explain the outcome and next step">${escapeHtml(item.resolution)}</textarea></label><label>Approver<input name="actor" required value="Demo quality manager"></label><label class="check-label"><input type="checkbox" name="reviewed" required> I reviewed RCA, CAPA and the customer response.</label><button class="button primary wide" type="submit">Approve resolution →</button></form>`}`;
  $('#case-dialog').showModal();
}

async function perform(path, data) {
  try { await api(path, { method: 'POST', body: JSON.stringify(data) }); await refresh(); await openCase(selectedId); toast('Case updated and audit entry recorded.'); }
  catch (error) { toast(error.message, true); }
}

$('#today').textContent = new Date().toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'long', year: 'numeric' });
$('#search').addEventListener('input', renderRows);
$('#status-filter').addEventListener('change', renderRows);
$('#refresh').addEventListener('click', () => refresh().then(() => toast('Queue refreshed.')).catch(e => toast(e.message, true)));
$('#case-rows').addEventListener('click', event => { const row = event.target.closest('tr[data-id]'); if (row) openCase(row.dataset.id).catch(e => toast(e.message, true)); });
$('#case-rows').addEventListener('keydown', event => { if (event.key === 'Enter') event.target.closest('tr[data-id]')?.click(); });
$('#new-case').addEventListener('click', () => $('#new-dialog').showModal());
$('#close-case').addEventListener('click', () => $('#case-dialog').close());
$('#close-new').addEventListener('click', () => $('#new-dialog').close());
$('#new-form').addEventListener('submit', async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  try { const result = await api('/api/complaints', { method: 'POST', body: JSON.stringify(data) }); $('#new-dialog').close(); event.target.reset(); await refresh(); await openCase(result.id); toast(`CC-${String(result.id).padStart(3,'0')} created. Review the suggested routing.`); }
  catch (error) { toast(error.message, true); }
});
$('#case-detail').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form));
  if (form.id === 'approve-form') data.reviewed = form.elements.reviewed.checked;
  const action = ({ 'assign-form': 'assign', 'rca-form': 'update', 'approve-form': 'approve' })[form.id];
  if (action) perform(`/api/complaints/${selectedId}/${action}`, data);
});
$('#assistant-form').addEventListener('submit', async event => {
  event.preventDefault();
  try { const data = await api('/api/assistant', { method: 'POST', body: JSON.stringify({ question: $('#assistant-question').value }) }); $('#assistant-answer').textContent = data.answer; }
  catch (error) { toast(error.message, true); }
});
refresh().catch(error => toast(`Could not load the demo: ${error.message}`, true));
