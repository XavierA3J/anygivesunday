const ownerSet = new Set();
GAMES.forEach(g => {
  if (g.home_owner) ownerSet.add(g.home_owner);
  if (g.away_owner) ownerSet.add(g.away_owner);
});
const OWNERS = Array.from(ownerSet).sort();

const seasonSelect = document.getElementById('filterSeason');
const managerSelect = document.getElementById('filterManager');
const typeSelect = document.getElementById('filterType');
const tbody = document.getElementById('logTbody');
const logCount = document.getElementById('logCount');
const h2hA = document.getElementById('h2hA');
const h2hB = document.getElementById('h2hB');
const h2hResult = document.getElementById('h2hResult');

const YEARS_PRESENT = Array.from(new Set(GAMES.map(g => g.year))).sort();
YEARS_PRESENT.forEach(y => {
  const opt = document.createElement('option');
  opt.value = y; opt.textContent = y;
  seasonSelect.appendChild(opt);
});
OWNERS.forEach(o => {
  const opt = document.createElement('option');
  opt.value = o; opt.textContent = o;
  managerSelect.appendChild(opt);
  const a = opt.cloneNode(true); h2hA.appendChild(a);
  const b = opt.cloneNode(true); h2hB.appendChild(b);
});
if (OWNERS.length > 1) { h2hA.selectedIndex = 0; h2hB.selectedIndex = 1; }

const TYPE_LABELS = {
  'NONE': 'Regular',
  'WINNERS_BRACKET': 'Playoff',
  'WINNERS_CONSOLATION_LADDER': 'Win. Consol.',
  'LOSERS_CONSOLATION_LADDER': 'Lose Consol.',
};
function isPlayoff(type) { return type !== 'NONE'; }

function renderLog() {
  const season = seasonSelect.value;
  const manager = managerSelect.value;
  const type = typeSelect.value;

  const filtered = GAMES.filter(g => {
    if (season !== 'all' && String(g.year) !== season) return false;
    if (type !== 'all' && g.type !== type) return false;
    if (manager !== 'all' && g.home_owner !== manager && g.away_owner !== manager) return false;
    if (!g.away_team) return false; // skip bye weeks in the log view
    return true;
  });

  logCount.textContent = `Showing ${filtered.length} of ${GAMES.length} games`;

  tbody.innerHTML = filtered.map(g => {
    const rowClass = isPlayoff(g.type) ? ' class="gg-log-playoff"' : '';
    const tagClass = isPlayoff(g.type) ? 'gg-tag gg-tag-playoff' : 'gg-tag';
    const homeWin = g.home_score > g.away_score;
    return `<tr${rowClass}>
      <td>${g.year}</td>
      <td>${g.week}</td>
      <td><span class="${tagClass}">${TYPE_LABELS[g.type] || g.type}</span></td>
      <td>${g.home_owner || ''} <span style="color:var(--chalk-dim);font-size:0.8em;">(${g.home_team})</span></td>
      <td class="gg-num" style="${homeWin ? 'color:var(--amber);font-weight:700;' : ''}">${g.home_score.toFixed(2)}</td>
      <td>${g.away_owner || ''} <span style="color:var(--chalk-dim);font-size:0.8em;">(${g.away_team})</span></td>
      <td class="gg-num" style="${!homeWin ? 'color:var(--amber);font-weight:700;' : ''}">${g.away_score.toFixed(2)}</td>
      <td class="gg-num">${g.margin != null ? g.margin.toFixed(1) : '—'}</td>
    </tr>`;
  }).join('');
}

function renderH2H() {
  const a = h2hA.value, b = h2hB.value;
  if (!a || !b || a === b) {
    h2hResult.textContent = 'Pick two different managers to see their all-time head-to-head record.';
    return;
  }
  const meetings = GAMES.filter(g =>
    (g.home_owner === a && g.away_owner === b) || (g.home_owner === b && g.away_owner === a)
  );
  if (meetings.length === 0) {
    h2hResult.textContent = `${a} and ${b} have never played each other.`;
    return;
  }
  let aWins = 0, bWins = 0, aPoints = 0, bPoints = 0;
  meetings.forEach(g => {
    const aIsHome = g.home_owner === a;
    const aScore = aIsHome ? g.home_score : g.away_score;
    const bScore = aIsHome ? g.away_score : g.home_score;
    aPoints += aScore; bPoints += bScore;
    if (aScore > bScore) aWins++; else if (bScore > aScore) bWins++;
  });
  h2hResult.innerHTML = `<strong>${a} ${aWins}&ndash;${bWins} ${b}</strong> across ${meetings.length} meetings &middot; `
    + `${a} has scored ${aPoints.toFixed(1)} combined points, ${b} has scored ${bPoints.toFixed(1)}.`;
}

seasonSelect.addEventListener('change', renderLog);
managerSelect.addEventListener('change', renderLog);
typeSelect.addEventListener('change', renderLog);
h2hA.addEventListener('change', renderH2H);
h2hB.addEventListener('change', renderH2H);

renderLog();
renderH2H();

