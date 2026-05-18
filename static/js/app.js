const state = {
  companies: [],
  leads: [],
  matches: [],
};

const $ = (selector) => document.querySelector(selector);

function setMessage(text, isError = false) {
  const el = $('#message');
  el.textContent = text;
  el.style.color = isError ? '#cf2e2e' : '#677083';
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function formToObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function populateSelects() {
  const companySelect = $('#companySelect');
  const leadSelect = $('#leadSelect');

  companySelect.innerHTML = '<option value="">All companies</option>';
  leadSelect.innerHTML = '<option value="">All leads</option>';

  state.companies.forEach((company) => {
    const option = document.createElement('option');
    option.value = company.id;
    option.textContent = `${company.name} — ${company.location}`;
    companySelect.appendChild(option);
  });

  state.leads.forEach((lead) => {
    const option = document.createElement('option');
    option.value = lead.id;
    option.textContent = `${lead.name} — ${lead.city}`;
    leadSelect.appendChild(option);
  });
}

function verdictLabel(verdict) {
  return verdict.replace('_', ' ');
}

function renderMatches() {
  const tbody = $('#matchesBody');
  const query = $('#searchInput').value.trim().toLowerCase();

  const filtered = state.matches.filter((match) => {
    const haystack = [
      match.company_name,
      match.lead_name,
      match.verdict,
      match.recommended_action,
      match.source,
      ...(match.reasons || []),
    ].join(' ').toLowerCase();
    return haystack.includes(query);
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="7">No matches yet. Run matching to create results.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map((match) => `
    <tr>
      <td><span class="score">${match.match_score ?? '-'}</span></td>
      <td><span class="badge ${match.verdict}">${verdictLabel(match.verdict)}</span></td>
      <td>${escapeHtml(match.company_name)}</td>
      <td>${escapeHtml(match.lead_name)}</td>
      <td>
        <ul class="reasons">
          ${(match.reasons || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}
        </ul>
      </td>
      <td>${escapeHtml(match.recommended_action || '')}</td>
      <td>${escapeHtml(match.source || '')}</td>
    </tr>
  `).join('');
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function loadAll() {
  const [status, companies, leads, matches] = await Promise.all([
    api('/api/status'),
    api('/api/companies'),
    api('/api/leads'),
    api('/api/matches'),
  ]);

  state.companies = companies;
  state.leads = leads;
  state.matches = matches;

  $('#apiStatus').textContent = status.openai_enabled
    ? `OpenAI enabled: ${status.model}`
    : 'OpenAI disabled: using local rules';
  $('#dbPath').textContent = `DB: ${status.database_path}`;

  populateSelects();
  renderMatches();
}

async function submitCompany(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api('/api/companies', {
      method: 'POST',
      body: JSON.stringify(formToObject(form)),
    });
    form.reset();
    setMessage('Company added.');
    await loadAll();
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function submitLead(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formToObject(form);
  payload.age = Number(payload.age);

  try {
    await api('/api/leads', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    form.reset();
    setMessage('Lead added.');
    await loadAll();
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function runMatching() {
  const runBtn = $('#runBtn');
  runBtn.disabled = true;
  setMessage('Running match assessments...');

  const payload = {};
  const companyId = $('#companySelect').value;
  const leadId = $('#leadSelect').value;
  if (companyId) payload.company_id = Number(companyId);
  if (leadId) payload.lead_id = Number(leadId);

  try {
    const result = await api('/api/match/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setMessage(`Created ${result.count} match assessment(s).`);
    await loadAll();
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    runBtn.disabled = false;
  }
}

async function clearMatches() {
  if (!confirm('Delete all saved match history? Companies and leads will stay.')) return;
  try {
    await api('/api/matches', { method: 'DELETE' });
    setMessage('Match history cleared.');
    await loadAll();
  } catch (error) {
    setMessage(error.message, true);
  }
}

$('#companyForm').addEventListener('submit', submitCompany);
$('#leadForm').addEventListener('submit', submitLead);
$('#runBtn').addEventListener('click', runMatching);
$('#clearBtn').addEventListener('click', clearMatches);
$('#refreshBtn').addEventListener('click', loadAll);
$('#searchInput').addEventListener('input', renderMatches);

loadAll().catch((error) => setMessage(error.message, true));
