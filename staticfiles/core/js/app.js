/**
 * Rajasthan Royals Scouting Engine — Application Logic & View Router
 * Modular, clean vanilla JavaScript application.
 */

// Application State
let overviewData = null;
let overviewTab = 'uncapped';       // 'uncapped', 'non_ipl', or 'all'
let finalTab = 'uncapped';          // 'uncapped', 'non_ipl', or 'all'

// API Client Helper
async function api(path) {
  try {
    const res = await fetch(`/api${path}`);
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("API Error:", path, err);
    throw err;
  }
}

// Navigation Tab Switcher
function setActiveNav(page) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
}

// Quick Search Handler (Header)
function handleQuickSearch(e) {
  if (e.key === 'Enter') {
    const q = e.target.value.trim();
    if (q) {
      location.hash = `#/players?q=${encodeURIComponent(q)}`;
    }
  }
}

// View Router
async function router() {
  const hash = location.hash.replace('#/', '') || 'overview';
  const [path, queryString] = hash.split('?');
  const params = new URLSearchParams(queryString || '');
  const container = document.getElementById('contentArea');

  setActiveNav(path);

  try {
    if (path === 'overview' || path === '') {
      document.getElementById('pageTitle').textContent = 'Dashboard Overview';
      document.getElementById('pageSub').textContent = 'High-stakes situational intelligence & uncapped prospect rankings';
      await renderOverview(container);
    } else if (path === 'batting') {
      document.getElementById('pageTitle').textContent = 'Batting Pressure Leaderboard';
      document.getElementById('pageSub').textContent = 'High-leverage strike rates, boundary ratios & pressure indices';
      await renderBatting(container, params);
    } else if (path === 'bowling') {
      document.getElementById('pageTitle').textContent = 'Bowling Pressure Leaderboard';
      document.getElementById('pageSub').textContent = 'Death overs economy, wicket strike rates & pressure control index';
      await renderBowling(container, params);
    } else if (path === 'players') {
      document.getElementById('pageTitle').textContent = 'Player Talent Pool';
      document.getElementById('pageSub').textContent = 'Filter by uncapped status, existing IPL franchise, and qualification';
      await renderPlayers(container, params);
    } else if (path === 'final') {
      document.getElementById('pageTitle').textContent = 'Official Top 10 Picks';
      document.getElementById('pageSub').textContent = 'Official SupeRR Selector Round 1 ranked lists for Unstop submission';
      await renderFinal(container);
    } else if (path === 'pressure') {
      document.getElementById('pageTitle').textContent = 'Pressure Methodology & Architecture';
      document.getElementById('pageSub').textContent = 'SSPE scoring models, delivery weighting & qualification criteria';
      await renderPressure(container);
    } else if (path === 'compare') {
      document.getElementById('pageTitle').textContent = 'Prospect Comparison';
      document.getElementById('pageSub').textContent = 'Head-to-head metrics under normal vs pressure conditions';
      await renderCompare(container, params);
    } else if (path === 'competitions') {
      document.getElementById('pageTitle').textContent = 'Competitions & Formats';
      document.getElementById('pageSub').textContent = 'IPL & international T20 dataset breakdown (2022–2026)';
      await renderCompetitions(container);
    }
  } catch (err) {
    container.innerHTML = `
      <div class="card" style="padding: 24px; text-align: center; color: var(--danger);">
        <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px;">Error Loading View</div>
        <div style="font-size: 12.5px; color: var(--slate-500);">${err.message}</div>
      </div>
    `;
  }
}

// 1. DASHBOARD OVERVIEW
async function renderOverview(container) {
  if (!overviewData) {
    container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading situational intelligence...</div></div>';
    overviewData = await api('/overview/');
  }

  const d = overviewData;
  let batters, bowlers;
  if (overviewTab === 'non_ipl') {
    batters = d.top_non_ipl_batters && d.top_non_ipl_batters.length ? d.top_non_ipl_batters : d.top_uncapped_batters.filter(b => !b.is_in_ipl_team);
    bowlers = d.top_non_ipl_bowlers && d.top_non_ipl_bowlers.length ? d.top_non_ipl_bowlers : d.top_uncapped_bowlers.filter(b => !b.is_in_ipl_team);
  } else if (overviewTab === 'uncapped') {
    batters = d.top_uncapped_batters;
    bowlers = d.top_uncapped_bowlers;
  } else {
    batters = d.top_batters;
    bowlers = d.top_bowlers;
  }

  container.innerHTML = `
    <!-- Top KPI Grid -->
    <div class="grid-4">
      <div class="stat-card">
        <div class="stat-card-header">
          <span class="stat-card-title">Talent Pool</span>
          <span class="stat-card-badge" style="background:var(--slate-100); color:var(--slate-700);">GLOBAL</span>
        </div>
        <div class="stat-value">${d.total_players.toLocaleString()}</div>
        <div class="stat-desc">Players evaluated in IPL & T20I (Pakistani excluded)</div>
      </div>

      <div class="stat-card" style="border-left: 3px solid var(--rr-pink);">
        <div class="stat-card-header">
          <span class="stat-card-title">Uncapped Prospects</span>
          <span class="stat-card-badge badge-uncapped">SCOUT TARGETS</span>
        </div>
        <div class="stat-value" style="color: var(--rr-pink);">${(d.total_uncapped_players || 467).toLocaleString()}</div>
        <div class="stat-desc">Domestic talents eligible for acquisition</div>
      </div>

      <div class="stat-card">
        <div class="stat-card-header">
          <span class="stat-card-title">Matches Analyzed</span>
          <span class="stat-card-badge" style="background:var(--slate-100); color:var(--slate-700);">2022–2026</span>
        </div>
        <div class="stat-value">${d.total_matches.toLocaleString()}</div>
        <div class="stat-desc">IPL editions & international fixtures</div>
      </div>

      <div class="stat-card">
        <div class="stat-card-header">
          <span class="stat-card-title">Pressure Balls</span>
          <span class="stat-card-badge" style="background:var(--rr-pink-light); color:var(--rr-pink-text);">27.0%</span>
        </div>
        <div class="stat-value">${d.pressure_deliveries.toLocaleString()}</div>
        <div class="stat-desc">High-leverage pressure deliveries</div>
      </div>
    </div>

    <!-- Mode Selector Toolbar -->
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Cohort Filter:</span>
        <div class="segmented-control">
          <button class="seg-btn ${overviewTab === 'uncapped' ? 'active' : ''}" onclick="switchOverviewTab('uncapped')">
            ⭐ All Uncapped Talent
          </button>
          <button class="seg-btn ${overviewTab === 'non_ipl' ? 'active' : ''}" onclick="switchOverviewTab('non_ipl')">
            🎯 Exclude Existing IPL Teams (Free Prospects)
          </button>
          <button class="seg-btn ${overviewTab === 'all' ? 'active' : ''}" onclick="switchOverviewTab('all')">
            All-Star Global Pool
          </button>
        </div>
      </div>
      <div style="font-size: 12px; color: var(--slate-500);">
        ${overviewTab === 'non_ipl' ? 'Filtering out players playing for existing IPL teams (e.g. Shashank Singh at PBKS)' : overviewTab === 'uncapped' ? 'Displaying top domestic performers without senior international caps' : 'Displaying all qualified players across IPL and international cricket'}
      </div>
    </div>

    <!-- Symmetrical Dual Leaderboards -->
    <div class="grid-2">
      <!-- Batters Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span>Top 10 Batters Under Pressure</span>
          </div>
          <a href="#/batting?uncapped=${overviewTab !== 'all' ? '1' : '0'}${overviewTab === 'non_ipl' ? '&exclude_ipl=1' : ''}" class="btn btn-outline btn-sm">Full Board &rarr;</a>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="text-align:center;">#</th>
                <th>Batter</th>
                <th>Current Team</th>
                <th style="text-align:right;">Pressure SR</th>
                <th style="text-align:right;">Normal SR</th>
                <th style="text-align:right;">Runs (Balls)</th>
                <th style="text-align:right;">Score</th>
              </tr>
            </thead>
            <tbody>
              ${batters.slice(0, 10).map((b, i) => `
                <tr>
                  <td class="rank-cell"><span class="rank-badge ${i < 3 ? 'rank-' + (i+1) : 'rank-n'}">${i + 1}</span></td>
                  <td class="player-name-cell">
                    <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${b.player_id})">${b.player_name}</a>
                  </td>
                  <td>
                    ${b.is_in_ipl_team ? `<span class="badge badge-team">${b.ipl_team}</span>` : `<span class="badge badge-free">Domestic Free Agent</span>`}
                  </td>
                  <td style="text-align:right; font-weight:700;">${b.pressure_strike_rate}</td>
                  <td style="text-align:right; color:var(--slate-500);">${b.normal_strike_rate}</td>
                  <td style="text-align:right; font-size:12px;">${b.pressure_runs} <span style="color:var(--slate-400)">(${b.pressure_balls})</span></td>
                  <td style="text-align:right;" class="score-cell">${b.batting_pressure_score}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Bowlers Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span>Top 10 Bowlers Under Pressure</span>
          </div>
          <a href="#/bowling?uncapped=${overviewTab !== 'all' ? '1' : '0'}${overviewTab === 'non_ipl' ? '&exclude_ipl=1' : ''}" class="btn btn-outline btn-sm">Full Board &rarr;</a>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="text-align:center;">#</th>
                <th>Bowler</th>
                <th>Current Team</th>
                <th style="text-align:right;">Pressure Econ</th>
                <th style="text-align:right;">Normal Econ</th>
                <th style="text-align:right;">Wkts (Overs)</th>
                <th style="text-align:right;">Score</th>
              </tr>
            </thead>
            <tbody>
              ${bowlers.slice(0, 10).map((b, i) => `
                <tr>
                  <td class="rank-cell"><span class="rank-badge ${i < 3 ? 'rank-' + (i+1) : 'rank-n'}">${i + 1}</span></td>
                  <td class="player-name-cell">
                    <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${b.player_id})">${b.player_name}</a>
                  </td>
                  <td>
                    ${b.is_in_ipl_team ? `<span class="badge badge-team">${b.ipl_team}</span>` : `<span class="badge badge-free">Domestic Free Agent</span>`}
                  </td>
                  <td style="text-align:right; font-weight:700;">${b.pressure_economy}</td>
                  <td style="text-align:right; color:var(--slate-500);">${b.normal_economy}</td>
                  <td style="text-align:right; font-size:12px;">${b.pressure_wickets} <span style="color:var(--slate-400)">(${b.pressure_overs} ov)</span></td>
                  <td style="text-align:right;" class="score-cell">${b.bowling_pressure_score}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function switchOverviewTab(tab) {
  overviewTab = tab;
  renderOverview(document.getElementById('contentArea'));
}

// 2. BATTING RANKINGS
async function renderBatting(container, params) {
  container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading batting rankings...</div></div>';

  const isUncapped = params.get('uncapped') === '1' || params.get('uncapped') === null;
  const excludeIPL = params.get('exclude_ipl') === '1';
  const iplTeam = params.get('ipl_team') || '';
  const season = params.get('season') || '';

  const query = new URLSearchParams({
    uncapped: isUncapped ? '1' : '0',
    exclude_ipl: excludeIPL ? '1' : '0',
    limit: '50'
  });
  if (iplTeam) query.set('ipl_team', iplTeam);
  if (season) query.set('season', season);

  const [res, overview] = await Promise.all([
    api(`/leaderboard/batting/?${query.toString()}`),
    overviewData ? Promise.resolve(overviewData) : api('/overview/')
  ]);
  overviewData = overview;

  container.innerHTML = `
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Cohort:</span>
        <div class="segmented-control">
          <button class="seg-btn ${isUncapped && !excludeIPL ? 'active' : ''}" onclick="applyBatParam('uncapped', '1', 'exclude_ipl', '0')">
            ⭐ All Uncapped
          </button>
          <button class="seg-btn ${excludeIPL ? 'active' : ''}" onclick="applyBatParam('uncapped', '1', 'exclude_ipl', '1')">
            🎯 Exclude Existing IPL
          </button>
          <button class="seg-btn ${!isUncapped ? 'active' : ''}" onclick="applyBatParam('uncapped', '0', 'exclude_ipl', '0')">
            All Players
          </button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-label">IPL Franchise:</span>
        <select class="select-control" onchange="applyBatFilter('ipl_team', this.value)">
          <option value="">All Teams / Uncontracted</option>
          ${overview.ipl_teams.map(t => `<option value="${t}" ${iplTeam === t ? 'selected' : ''}>${t}</option>`).join('')}
        </select>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <span>Batting Pressure Leaders ${excludeIPL ? '(Uncontracted / Free Prospects)' : isUncapped ? '(Uncapped Prospects)' : '(All Qualified)'}</span>
        </div>
        <div style="font-size: 11.5px; color: var(--slate-500);">
          Min. 40 pressure balls faced & 5+ matches
        </div>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th style="text-align:center;">#</th>
              <th>Batter</th>
              <th>Franchise / Status</th>
              <th>Eligibility</th>
              <th style="text-align:right;">Pressure SR</th>
              <th style="text-align:right;">Normal SR</th>
              <th style="text-align:right;">SR Multiplier</th>
              <th style="text-align:right;">Pressure Runs</th>
              <th style="text-align:right;">Pressure Balls</th>
              <th style="text-align:right;">Boundaries</th>
              <th style="text-align:right;">Matches</th>
              <th style="text-align:right;">Score</th>
            </tr>
          </thead>
          <tbody>
            ${res.results.map((b, i) => `
              <tr>
                <td class="rank-cell"><span class="rank-badge ${i < 3 ? 'rank-' + (i+1) : 'rank-n'}">${b.rank}</span></td>
                <td class="player-name-cell">
                  <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${b.player_id})">${b.player_name}</a>
                </td>
                <td>
                  ${b.is_in_ipl_team ? `<span class="badge badge-team">${b.ipl_team}</span>` : `<span class="badge badge-free">Domestic Free Agent</span>`}
                </td>
                <td>
                  ${b.is_uncapped ? '<span class="badge badge-uncapped">UNCAPPED</span>' : '<span class="badge badge-capped">CAPPED</span>'}
                </td>
                <td style="text-align:right; font-weight:700;">${b.pressure_strike_rate}</td>
                <td style="text-align:right; color:var(--slate-500);">${b.normal_strike_rate}</td>
                <td style="text-align:right; color:${b.pressure_sr_ratio >= 1.0 ? 'var(--success)' : 'var(--slate-500)'}; font-weight:600;">
                  ${b.pressure_sr_ratio}x
                </td>
                <td style="text-align:right;">${b.pressure_runs}</td>
                <td style="text-align:right;">${b.pressure_balls}</td>
                <td style="text-align:right;">${b.pressure_boundaries}</td>
                <td style="text-align:right;">${b.matches}</td>
                <td style="text-align:right;" class="score-cell">${b.batting_pressure_score}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function applyBatFilter(key, val) {
  const p = new URLSearchParams(location.hash.split('?')[1] || '');
  if (val) p.set(key, val);
  else p.delete(key);
  location.hash = `#/batting?${p.toString()}`;
}

function applyBatParam(k1, v1, k2, v2) {
  const p = new URLSearchParams(location.hash.split('?')[1] || '');
  p.set(k1, v1);
  p.set(k2, v2);
  location.hash = `#/batting?${p.toString()}`;
}

// 3. BOWLING RANKINGS
async function renderBowling(container, params) {
  container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading bowling rankings...</div></div>';

  const isUncapped = params.get('uncapped') === '1' || params.get('uncapped') === null;
  const excludeIPL = params.get('exclude_ipl') === '1';
  const iplTeam = params.get('ipl_team') || '';
  const season = params.get('season') || '';

  const query = new URLSearchParams({
    uncapped: isUncapped ? '1' : '0',
    exclude_ipl: excludeIPL ? '1' : '0',
    limit: '50'
  });
  if (iplTeam) query.set('ipl_team', iplTeam);
  if (season) query.set('season', season);

  const [res, overview] = await Promise.all([
    api(`/leaderboard/bowling/?${query.toString()}`),
    overviewData ? Promise.resolve(overviewData) : api('/overview/')
  ]);
  overviewData = overview;

  container.innerHTML = `
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Cohort:</span>
        <div class="segmented-control">
          <button class="seg-btn ${isUncapped && !excludeIPL ? 'active' : ''}" onclick="applyBowlParam('uncapped', '1', 'exclude_ipl', '0')">
            ⭐ All Uncapped
          </button>
          <button class="seg-btn ${excludeIPL ? 'active' : ''}" onclick="applyBowlParam('uncapped', '1', 'exclude_ipl', '1')">
            🎯 Exclude Existing IPL
          </button>
          <button class="seg-btn ${!isUncapped ? 'active' : ''}" onclick="applyBowlParam('uncapped', '0', 'exclude_ipl', '0')">
            All Players
          </button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-label">IPL Franchise:</span>
        <select class="select-control" onchange="applyBowlFilter('ipl_team', this.value)">
          <option value="">All Teams / Uncontracted</option>
          ${overview.ipl_teams.map(t => `<option value="${t}" ${iplTeam === t ? 'selected' : ''}>${t}</option>`).join('')}
        </select>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <span>Bowling Pressure Leaders ${excludeIPL ? '(Uncontracted / Free Prospects)' : isUncapped ? '(Uncapped Prospects)' : '(All Qualified)'}</span>
        </div>
        <div style="font-size: 11.5px; color: var(--slate-500);">
          Min. 60 pressure balls (10 overs) & 5+ matches
        </div>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th style="text-align:center;">#</th>
              <th>Bowler</th>
              <th>Franchise / Status</th>
              <th>Eligibility</th>
              <th style="text-align:right;">Pressure Econ</th>
              <th style="text-align:right;">Normal Econ</th>
              <th style="text-align:right;">Econ Ratio</th>
              <th style="text-align:right;">Pressure Wkts</th>
              <th style="text-align:right;">Total Wkts</th>
              <th style="text-align:right;">Pressure Overs</th>
              <th style="text-align:right;">Matches</th>
              <th style="text-align:right;">Score</th>
            </tr>
          </thead>
          <tbody>
            ${res.results.map((b, i) => `
              <tr>
                <td class="rank-cell"><span class="rank-badge ${i < 3 ? 'rank-' + (i+1) : 'rank-n'}">${b.rank}</span></td>
                <td class="player-name-cell">
                  <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${b.player_id})">${b.player_name}</a>
                </td>
                <td>
                  ${b.is_in_ipl_team ? `<span class="badge badge-team">${b.ipl_team}</span>` : `<span class="badge badge-free">Domestic Free Agent</span>`}
                </td>
                <td>
                  ${b.is_uncapped ? '<span class="badge badge-uncapped">UNCAPPED</span>' : '<span class="badge badge-capped">CAPPED</span>'}
                </td>
                <td style="text-align:right; font-weight:700;">${b.pressure_economy}</td>
                <td style="text-align:right; color:var(--slate-500);">${b.normal_economy}</td>
                <td style="text-align:right; color:${b.pressure_economy_ratio >= 1.0 ? 'var(--success)' : 'var(--slate-500)'}; font-weight:600;">
                  ${b.pressure_economy_ratio}x
                </td>
                <td style="text-align:right; font-weight:600;">${b.pressure_wickets}</td>
                <td style="text-align:right; color:var(--slate-500);">${b.total_wickets}</td>
                <td style="text-align:right;">${b.pressure_overs} ov</td>
                <td style="text-align:right;">${b.matches}</td>
                <td style="text-align:right;" class="score-cell">${b.bowling_pressure_score}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function applyBowlFilter(key, val) {
  const p = new URLSearchParams(location.hash.split('?')[1] || '');
  if (val) p.set(key, val);
  else p.delete(key);
  location.hash = `#/bowling?${p.toString()}`;
}

function applyBowlParam(k1, v1, k2, v2) {
  const p = new URLSearchParams(location.hash.split('?')[1] || '');
  p.set(k1, v1);
  p.set(k2, v2);
  location.hash = `#/bowling?${p.toString()}`;
}

// 4. TALENT POOL
async function renderPlayers(container, params) {
  container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading talent pool...</div></div>';

  const q = params.get('q') || '';
  const role = params.get('role') || '';
  const isUncapped = params.get('uncapped') === '1';
  const excludeIPL = params.get('exclude_ipl') === '1';
  const iplTeam = params.get('ipl_team') || '';
  const page = parseInt(params.get('page') || '1', 10);

  const query = new URLSearchParams({
    q, role,
    uncapped: isUncapped ? '1' : '0',
    exclude_ipl: excludeIPL ? '1' : '0',
    page: String(page),
    page_size: '25'
  });
  if (iplTeam) query.set('ipl_team', iplTeam);

  const res = await api(`/players/?${query.toString()}`);

  container.innerHTML = `
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Search:</span>
        <input type="text" id="playerPoolSearch" class="search-input" style="width:190px; padding-left:10px;" placeholder="Filter name..." value="${q}" onkeydown="if(event.key==='Enter') executePlayerSearch()">
        <button class="btn btn-outline btn-sm" onclick="executePlayerSearch()">Search</button>
      </div>

      <div class="filter-group">
        <span class="filter-label">Role:</span>
        <select class="select-control" id="roleSelect" onchange="executePlayerSearch()">
          <option value="">All Roles</option>
          <option value="batting" ${role === 'batting' ? 'selected' : ''}>Qualified Batters</option>
          <option value="bowling" ${role === 'bowling' ? 'selected' : ''}>Qualified Bowlers</option>
          <option value="allrounder" ${role === 'allrounder' ? 'selected' : ''}>All-Rounders</option>
        </select>

        <span class="filter-label" style="margin-left:6px;">Franchise:</span>
        <select class="select-control" id="teamSelect" onchange="executePlayerSearch()">
          <option value="">All Teams / Free Agents</option>
          ${(res.ipl_teams || []).map(t => `<option value="${t}" ${iplTeam === t ? 'selected' : ''}>${t}</option>`).join('')}
        </select>

        <label style="display:flex; align-items:center; gap:5px; font-size:12px; font-weight:600; cursor:pointer; margin-left:8px;">
          <input type="checkbox" id="uncappedCheck" ${isUncapped ? 'checked' : ''} onchange="executePlayerSearch()">
          <span>Uncapped Only</span>
        </label>

        <label style="display:flex; align-items:center; gap:5px; font-size:12px; font-weight:600; cursor:pointer; margin-left:8px;">
          <input type="checkbox" id="excludeIPLCheck" ${excludeIPL ? 'checked' : ''} onchange="executePlayerSearch()">
          <span>Exclude Existing IPL</span>
        </label>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <span>Player Talent Pool (${res.total.toLocaleString()} players)</span>
        </div>
        <div style="font-size:11.5px; color:var(--slate-500);">
          Page ${res.page} of ${res.total_pages}
        </div>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Player Name</th>
              <th>Current Franchise</th>
              <th>Status</th>
              <th style="text-align:right;">Bat Score</th>
              <th style="text-align:right;">Pressure SR</th>
              <th style="text-align:right;">Normal SR</th>
              <th style="text-align:right;">Bat M</th>
              <th style="text-align:right;">Bowl Score</th>
              <th style="text-align:right;">Pressure Econ</th>
              <th style="text-align:right;">Pressure Wkts</th>
              <th style="text-align:right;">Bowl M</th>
            </tr>
          </thead>
          <tbody>
            ${res.results.map(p => `
              <tr>
                <td class="player-name-cell">
                  <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${p.player_id})">${p.player_name}</a>
                </td>
                <td>
                  ${p.is_in_ipl_team ? `<span class="badge badge-team">${p.ipl_team}</span>` : `<span class="badge badge-free">Domestic Free Agent</span>`}
                </td>
                <td>
                  ${p.is_uncapped ? '<span class="badge badge-uncapped">UNCAPPED</span>' : '<span class="badge badge-capped">CAPPED</span>'}
                </td>
                <td style="text-align:right;" class="score-cell">${p.batting_score || '—'}</td>
                <td style="text-align:right;">${p.pressure_sr ? p.pressure_sr : '—'}</td>
                <td style="text-align:right; color:var(--slate-500);">${p.normal_sr ? p.normal_sr : '—'}</td>
                <td style="text-align:right;">${p.batting_matches}</td>
                <td style="text-align:right;" class="score-cell">${p.bowling_score || '—'}</td>
                <td style="text-align:right;">${p.pressure_econ ? p.pressure_econ : '—'}</td>
                <td style="text-align:right;">${p.pressure_wickets}</td>
                <td style="text-align:right;">${p.bowling_matches}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    <div style="display:flex; justify-content:center; gap:8px; margin-top:16px;">
      ${page > 1 ? `<button class="btn btn-outline btn-sm" onclick="goToPlayerPage(${page - 1})">&larr; Previous</button>` : ''}
      <span style="font-size:12px; color:var(--slate-500); align-self:center;">Page ${page} of ${res.total_pages}</span>
      ${page < res.total_pages ? `<button class="btn btn-outline btn-sm" onclick="goToPlayerPage(${page + 1})">Next &rarr;</button>` : ''}
    </div>
  `;
}

function executePlayerSearch() {
  const q = document.getElementById('playerPoolSearch').value.trim();
  const role = document.getElementById('roleSelect').value;
  const iplTeam = document.getElementById('teamSelect').value;
  const uncapped = document.getElementById('uncappedCheck').checked;
  const excludeIPL = document.getElementById('excludeIPLCheck').checked;
  const p = new URLSearchParams();
  if (q) p.set('q', q);
  if (role) p.set('role', role);
  if (iplTeam) p.set('ipl_team', iplTeam);
  if (uncapped) p.set('uncapped', '1');
  if (excludeIPL) p.set('exclude_ipl', '1');
  location.hash = `#/players?${p.toString()}`;
}

function goToPlayerPage(pNum) {
  const p = new URLSearchParams(location.hash.split('?')[1] || '');
  p.set('page', String(pNum));
  location.hash = `#/players?${p.toString()}`;
}

// 5. OFFICIAL TOP 10 PICKS (SupeRR Selector Submission)
async function renderFinal(container) {
  if (!overviewData) overviewData = await api('/overview/');
  const d = overviewData;

  let batters, bowlers;
  if (finalTab === 'non_ipl') {
    batters = d.top_non_ipl_batters && d.top_non_ipl_batters.length ? d.top_non_ipl_batters : d.top_uncapped_batters.filter(b => !b.is_in_ipl_team);
    bowlers = d.top_non_ipl_bowlers && d.top_non_ipl_bowlers.length ? d.top_non_ipl_bowlers : d.top_uncapped_bowlers.filter(b => !b.is_in_ipl_team);
  } else if (finalTab === 'uncapped') {
    batters = d.top_uncapped_batters;
    bowlers = d.top_uncapped_bowlers;
  } else {
    batters = d.top_batters;
    bowlers = d.top_bowlers;
  }

  container.innerHTML = `
    <!-- Submission Banner -->
    <div class="card" style="padding: 18px; margin-bottom: 18px; border-left: 4px solid var(--rr-pink);">
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="font-size: 16px; font-weight: 800; color: var(--slate-900);">
            SupeRR Selector Season 2 — Official Ranked Submissions
          </div>
          <div style="font-size: 12px; color: var(--slate-500); margin-top: 2px;">
            Two ordered top-10 lists required for Unstop dropdown fields: Top 10 Batters & Top 10 Bowlers.
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <button class="btn btn-outline btn-sm" onclick="copySubmissionText()">
            📋 Copy Unstop List
          </button>
          <button class="btn btn-primary btn-sm" onclick="downloadSubmissionCSV()">
            📥 Export CSV
          </button>
        </div>
      </div>
    </div>

    <!-- Cohort Selector -->
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Submission Category:</span>
        <div class="segmented-control">
          <button class="seg-btn ${finalTab === 'uncapped' ? 'active' : ''}" onclick="switchFinalTab('uncapped')">
            ⭐ All Uncapped Prospects (Round 1 Priority)
          </button>
          <button class="seg-btn ${finalTab === 'non_ipl' ? 'active' : ''}" onclick="switchFinalTab('non_ipl')">
            🎯 Exclude Existing IPL (Free Prospects)
          </button>
          <button class="seg-btn ${finalTab === 'all' ? 'active' : ''}" onclick="switchFinalTab('all')">
            All-Star Global Pool
          </button>
        </div>
      </div>
      <div style="font-size: 11.5px; color: var(--slate-500);">
        Rank 1 is the highest-rated player in each category as per SupeRR Selector guidelines.
      </div>
    </div>

    <!-- Symmetrical Top 10 Cards -->
    <div class="grid-2">
      <!-- Batters Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span>Top 10 Batters Under Pressure</span>
          </div>
          <span class="badge ${finalTab !== 'all' ? 'badge-uncapped' : 'badge-capped'}">
            ${finalTab === 'non_ipl' ? 'FREE PROSPECTS' : finalTab === 'uncapped' ? 'UNCAPPED FOCUS' : 'GLOBAL POOL'}
          </span>
        </div>
        <div style="padding: 12px;">
          ${batters.slice(0, 10).map((b, i) => `
            <div class="sub-item">
              <div class="sub-left">
                <span class="sub-rank">#${i + 1}</span>
                <div>
                  <div class="sub-name">
                    <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${b.player_id})">${b.player_name}</a>
                    <span style="font-size:11px; margin-left:6px; font-weight:normal;">
                      ${b.is_in_ipl_team ? `<span class="badge badge-team">${b.ipl_team}</span>` : `<span class="badge badge-free">Free Agent</span>`}
                    </span>
                  </div>
                  <div class="sub-meta">
                    Pressure SR: <strong>${b.pressure_strike_rate}</strong> | Normal SR: ${b.normal_strike_rate} | Runs: ${b.pressure_runs} (${b.pressure_balls}b)
                  </div>
                </div>
              </div>
              <div class="sub-score">
                <div>${b.batting_pressure_score}</div>
                <div style="font-size:10px; color:var(--slate-500); font-weight:500;">Index</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Bowlers Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span>Top 10 Bowlers Under Pressure</span>
          </div>
          <span class="badge ${finalTab !== 'all' ? 'badge-uncapped' : 'badge-capped'}">
            ${finalTab === 'non_ipl' ? 'FREE PROSPECTS' : finalTab === 'uncapped' ? 'UNCAPPED FOCUS' : 'GLOBAL POOL'}
          </span>
        </div>
        <div style="padding: 12px;">
          ${bowlers.slice(0, 10).map((b, i) => `
            <div class="sub-item">
              <div class="sub-left">
                <span class="sub-rank">#${i + 1}</span>
                <div>
                  <div class="sub-name">
                    <a href="javascript:void(0)" class="player-link" onclick="openPlayerModal(${b.player_id})">${b.player_name}</a>
                    <span style="font-size:11px; margin-left:6px; font-weight:normal;">
                      ${b.is_in_ipl_team ? `<span class="badge badge-team">${b.ipl_team}</span>` : `<span class="badge badge-free">Free Agent</span>`}
                    </span>
                  </div>
                  <div class="sub-meta">
                    Pressure Econ: <strong>${b.pressure_economy}</strong> | Wkts: ${b.pressure_wickets} (${b.pressure_overs} ov) | Matches: ${b.matches}
                  </div>
                </div>
              </div>
              <div class="sub-score">
                <div>${b.bowling_pressure_score}</div>
                <div style="font-size:10px; color:var(--slate-500); font-weight:500;">Index</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
}

function switchFinalTab(tab) {
  finalTab = tab;
  renderFinal(document.getElementById('contentArea'));
}

function copySubmissionText() {
  if (!overviewData) return;
  let batters, bowlers;
  if (finalTab === 'non_ipl') {
    batters = overviewData.top_non_ipl_batters || overviewData.top_uncapped_batters.filter(b => !b.is_in_ipl_team);
    bowlers = overviewData.top_non_ipl_bowlers || overviewData.top_uncapped_bowlers.filter(b => !b.is_in_ipl_team);
  } else if (finalTab === 'uncapped') {
    batters = overviewData.top_uncapped_batters;
    bowlers = overviewData.top_uncapped_bowlers;
  } else {
    batters = overviewData.top_batters;
    bowlers = overviewData.top_bowlers;
  }

  let text = `=== SUPERR SELECTOR SEASON 2 SUBMISSION (${finalTab.toUpperCase()}) ===\n\n`;
  text += `--- TOP 10 BATTERS UNDER PRESSURE ---\n`;
  batters.slice(0, 10).forEach((b, idx) => {
    text += `Rank ${idx + 1}: ${b.player_name} [${b.ipl_team}] (Score: ${b.batting_pressure_score}, Pressure SR: ${b.pressure_strike_rate}, Normal SR: ${b.normal_strike_rate})\n`;
  });
  text += `\n--- TOP 10 BOWLERS UNDER PRESSURE ---\n`;
  bowlers.slice(0, 10).forEach((b, idx) => {
    text += `Rank ${idx + 1}: ${b.player_name} [${b.ipl_team}] (Score: ${b.bowling_pressure_score}, Pressure Econ: ${b.pressure_economy}, Wkts: ${b.pressure_wickets})\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    alert("Top 10 Submission list copied to clipboard! You can paste it into Unstop or your submission report.");
  });
}

function downloadSubmissionCSV() {
  if (!overviewData) return;
  let batters, bowlers;
  if (finalTab === 'non_ipl') {
    batters = overviewData.top_non_ipl_batters || overviewData.top_uncapped_batters.filter(b => !b.is_in_ipl_team);
    bowlers = overviewData.top_non_ipl_bowlers || overviewData.top_uncapped_bowlers.filter(b => !b.is_in_ipl_team);
  } else if (finalTab === 'uncapped') {
    batters = overviewData.top_uncapped_batters;
    bowlers = overviewData.top_uncapped_bowlers;
  } else {
    batters = overviewData.top_batters;
    bowlers = overviewData.top_bowlers;
  }

  let csv = "category,rank,player_id,player_name,ipl_team,is_in_ipl_team,pressure_score,primary_pressure_metric,primary_normal_metric,matches\n";
  batters.slice(0, 10).forEach((b, idx) => {
    csv += `Batter,${idx + 1},${b.player_id},"${b.player_name}","${b.ipl_team}",${b.is_in_ipl_team},${b.batting_pressure_score},${b.pressure_strike_rate},${b.normal_strike_rate},${b.matches}\n`;
  });
  bowlers.slice(0, 10).forEach((b, idx) => {
    csv += `Bowler,${idx + 1},${b.player_id},"${b.player_name}","${b.ipl_team}",${b.is_in_ipl_team},${b.bowling_pressure_score},${b.pressure_economy},${b.normal_economy},${b.matches}\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `rr_superr_selector_top10_${finalTab}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// 6. PRESSURE METHODOLOGY
async function renderPressure(container) {
  container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading methodology...</div></div>';
  const m = await api('/methodology/');

  container.innerHTML = `
    <div class="card" style="padding: 18px; margin-bottom: 18px;">
      <div style="font-size: 15px; font-weight: 800; color: var(--slate-900);">${m.framework_name}</div>
      <p style="font-size: 12.5px; color: var(--slate-500); margin-top: 4px; line-height: 1.6;">${m.description}</p>
    </div>

    <div class="grid-2" style="margin-bottom: 18px;">
      <!-- Situational Rules Table -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Situational Pressure Signals</div>
          <span class="badge badge-uncapped">THRESHOLD &ge; 1.5</span>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Trigger Condition</th>
                <th>Weight</th>
              </tr>
            </thead>
            <tbody>
              ${m.delivery_rules.map(r => `
                <tr>
                  <td style="font-weight:700;">${r.category}</td>
                  <td>${r.condition}</td>
                  <td style="font-weight:600; color:var(--rr-pink);">${r.weight}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Uncapped & Franchise Scouting Policy -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Talent Discovery & Franchise Filtering</div>
          <span class="badge badge-uncapped">SCOUTING POLICY</span>
        </div>
        <div style="padding: 16px; font-size: 12.5px; color: var(--slate-700); line-height: 1.6;">
          <div style="margin-bottom: 10px;">
            <strong style="color:var(--slate-900);">Uncapped Definition:</strong> Players who have NEVER represented their senior national team in international cricket (No T20I / ODI / Test appearances).
          </div>
          <div style="margin-bottom: 10px;">
            <strong style="color:var(--slate-900);">Existing IPL Filter:</strong> Allows filtering out players already signed by other franchises (e.g. Shashank Singh at PBKS, Sai Sudharsan at GT) to isolate uncontracted domestic free agents for Rajasthan Royals auction targets.
          </div>
          <div style="background:var(--slate-50); border:1px solid var(--border); padding:10px 14px; border-radius:var(--radius-sm);">
            <div style="font-weight:700; color:var(--rr-pink); margin-bottom:4px;">Sample Size Calibration:</div>
            <ul style="padding-left:16px; color:var(--slate-500); font-size:11.5px;">
              <li>Batters: &ge; 40 pressure balls faced and &ge; 5 matches</li>
              <li>Bowlers: &ge; 60 pressure balls (10 overs) and &ge; 5 matches</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Scoring Formulas -->
    <div class="card" style="padding: 18px;">
      <div style="font-size: 13.5px; font-weight: 700; margin-bottom: 12px;">Quantitative Scoring Formulas</div>
      <div class="grid-2">
        <div style="background:var(--slate-50); border:1px solid var(--border); padding:14px; border-radius:var(--radius-sm);">
          <div style="font-weight:700; color:var(--rr-pink);">Batting Pressure Index Formula</div>
          <div style="font-family:monospace; font-size:11.5px; margin: 8px 0; background:#fff; padding:8px; border:1px solid var(--border); border-radius:4px;">
            Index = [ (SR_ratio &times; 0.40) + (Boundary_ratio &times; 0.30) + (Sample_weight &times; 0.30) ] &times; 70.0
          </div>
          <p style="font-size:11.5px; color:var(--slate-500);">Rewards batters who maintain or accelerate strike rate and boundary frequency during high-stress deliveries.</p>
        </div>

        <div style="background:var(--slate-50); border:1px solid var(--border); padding:14px; border-radius:var(--radius-sm);">
          <div style="font-weight:700; color:var(--rr-pink);">Bowling Pressure Index Formula</div>
          <div style="font-family:monospace; font-size:11.5px; margin: 8px 0; background:#fff; padding:8px; border:1px solid var(--border); border-radius:4px;">
            Index = [ (Econ_ratio &times; 0.45) + (Wicket_impact &times; 0.35) + (Consistency &times; 0.20) ] &times; 70.0
          </div>
          <p style="font-size:11.5px; color:var(--slate-500);">Rewards bowlers who stifle runs and take critical breakthroughs when games hang in the balance.</p>
        </div>
      </div>
    </div>
  `;
}

// 7. PROSPECT COMPARISON
async function renderCompare(container, params) {
  const ids = params.get('ids') || '2756,8101,6460'; // Default: Shashank Singh, Ashutosh Sharma, Ayush Badoni
  container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading comparison...</div></div>';

  const res = await api(`/compare/?ids=${ids}`);

  container.innerHTML = `
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Player IDs:</span>
        <input type="text" id="compareInput" class="search-input" style="width:240px; padding-left:10px;" value="${ids}" placeholder="e.g. 2756,8101,6460">
        <button class="btn btn-primary btn-sm" onclick="location.hash='#/compare?ids='+document.getElementById('compareInput').value">Compare</button>
      </div>
      <div style="font-size:11.5px; color:var(--slate-500);">Compare up to 4 players side by side</div>
    </div>

    <div style="display:grid; grid-template-columns: repeat(${res.players.length}, 1fr); gap: 16px;">
      ${res.players.map(p => `
        <div class="card" style="padding: 18px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <div style="font-size:15px; font-weight:800;">${p.player_name}</div>
              <div style="margin-top:4px; display:flex; gap:4px; flex-wrap:wrap;">
                ${p.is_in_ipl_team ? `<span class="badge badge-team">${p.ipl_team}</span>` : `<span class="badge badge-free">Free Agent</span>`}
                ${p.is_uncapped ? '<span class="badge badge-uncapped">UNCAPPED</span>' : '<span class="badge badge-capped">CAPPED</span>'}
              </div>
            </div>
          </div>

          <!-- Batting Section -->
          <div style="background:var(--slate-50); border:1px solid var(--border); padding:12px; border-radius:var(--radius-sm); margin-bottom:12px;">
            <div style="font-size:11.5px; font-weight:700; color:var(--rr-pink); margin-bottom:6px;">BATTING PROFILE</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--slate-500);">Pressure Score:</span>
              <strong class="score-cell">${p.batting.score || '—'}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--slate-500);">Pressure SR:</span>
              <strong>${p.batting.pressure_sr || '—'}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--slate-500);">Normal SR:</span>
              <span>${p.batting.normal_sr || '—'}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px;">
              <span style="color:var(--slate-500);">Pressure Runs:</span>
              <span>${p.batting.pressure_runs} (${p.batting.pressure_balls}b)</span>
            </div>
          </div>

          <!-- Bowling Section -->
          <div style="background:var(--slate-50); border:1px solid var(--border); padding:12px; border-radius:var(--radius-sm);">
            <div style="font-size:11.5px; font-weight:700; color:var(--rr-pink); margin-bottom:6px;">BOWLING PROFILE</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--slate-500);">Pressure Score:</span>
              <strong class="score-cell">${p.bowling.score || '—'}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--slate-500);">Pressure Econ:</span>
              <strong>${p.bowling.pressure_econ || '—'}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--slate-500);">Normal Econ:</span>
              <span>${p.bowling.normal_econ || '—'}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px;">
              <span style="color:var(--slate-500);">Pressure Wkts:</span>
              <span>${p.bowling.pressure_wickets} (${p.bowling.pressure_overs} ov)</span>
            </div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// 8. COMPETITIONS
async function renderCompetitions(container) {
  container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading competitions...</div></div>';
  const res = await api('/competitions/');

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">Ingested Competitions (${res.competitions.length} series)</div>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Competition</th>
              <th>Format</th>
              <th>Season</th>
              <th style="text-align:right;">Matches Recorded</th>
            </tr>
          </thead>
          <tbody>
            ${res.competitions.map(c => `
              <tr>
                <td style="font-weight:600;">${c.comp_name}</td>
                <td>
                  <span class="badge ${c.match_format === 'T20I' ? 'badge-capped' : 'badge-uncapped'}">${c.match_format}</span>
                </td>
                <td>${c.season}</td>
                <td style="text-align:right;">${c.match_count}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// Modal Player Profile
async function openPlayerModal(playerId) {
  const modal = document.getElementById('playerModal');
  const body = document.getElementById('modalBody');
  modal.classList.add('open');
  body.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div><div>Loading profile...</div></div>';

  try {
    const p = await api(`/players/${playerId}/`);
    document.getElementById('modalPlayerName').textContent = p.player_name;

    body.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:16px;">
        ${p.is_in_ipl_team ? `<span class="badge badge-team">${p.ipl_team}</span>` : `<span class="badge badge-free">Domestic Free Agent</span>`}
        ${p.is_uncapped ? '<span class="badge badge-uncapped">UNCAPPED PROSPECT</span>' : '<span class="badge badge-capped">CAPPED INTERNATIONAL</span>'}
        <span style="font-size:11.5px; color:var(--slate-500);">ID: ${p.player_id}</span>
      </div>

      <div class="grid-2" style="margin-bottom:16px;">
        <div style="background:var(--slate-50); border:1px solid var(--border); padding:14px; border-radius:var(--radius-sm);">
          <div style="font-size:11.5px; font-weight:700; color:var(--rr-pink); margin-bottom:4px;">BATTING PRESSURE PROFILE</div>
          <div style="font-size:22px; font-weight:800; color:var(--rr-pink); margin-bottom:4px;">${p.batting.pressure_score || '—'}</div>
          <div style="font-size:12px; color:var(--slate-600); line-height:1.5;">
            Pressure SR: <strong>${p.batting.pressure_strike_rate || '—'}</strong> (Normal: ${p.batting.normal_strike_rate || '—'})<br>
            Pressure Runs: <strong>${p.batting.pressure_runs}</strong> in ${p.batting.pressure_balls} balls<br>
            Boundaries Under Pressure: ${p.batting.pressure_fours} fours, ${p.batting.pressure_sixes} sixes
          </div>
        </div>

        <div style="background:var(--slate-50); border:1px solid var(--border); padding:14px; border-radius:var(--radius-sm);">
          <div style="font-size:11.5px; font-weight:700; color:var(--rr-pink); margin-bottom:4px;">BOWLING PRESSURE PROFILE</div>
          <div style="font-size:22px; font-weight:800; color:var(--rr-pink); margin-bottom:4px;">${p.bowling.pressure_score || '—'}</div>
          <div style="font-size:12px; color:var(--slate-600); line-height:1.5;">
            Pressure Economy: <strong>${p.bowling.pressure_economy || '—'}</strong> (Normal: ${p.bowling.normal_economy || '—'})<br>
            Pressure Wickets: <strong>${p.bowling.pressure_wickets}</strong> (${roundBalls(p.bowling.pressure_balls)} ov)<br>
            Economy Ratio: ${p.bowling.pressure_economy_ratio ? p.bowling.pressure_economy_ratio + 'x' : '—'}
          </div>
        </div>
      </div>

      <div style="margin-top:16px;">
        <div style="font-size:12.5px; font-weight:700; margin-bottom:8px;">Recent Matches</div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Stage</th>
              <th>Versus</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            ${p.recent_matches.map(m => `
              <tr>
                <td>${m.date}</td>
                <td>${m.stage}</td>
                <td>${m.vs}</td>
                <td style="font-size:11px; color:var(--slate-500);">${m.result}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div style="color:var(--danger); padding:16px;">Failed to load player details.</div>`;
  }
}

function roundBalls(b) {
  if (!b) return '0.0';
  return `${Math.floor(b / 6)}.${b % 6}`;
}

function closePlayerModal() {
  document.getElementById('playerModal').classList.remove('open');
}

// Global modal dismiss
window.onclick = function(e) {
  const modal = document.getElementById('playerModal');
  if (e.target === modal) closePlayerModal();
};

// Route Listener
window.addEventListener('hashchange', router);
window.addEventListener('load', router);
