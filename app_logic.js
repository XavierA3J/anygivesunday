
(function() {
  const searchInput = document.getElementById('playerSearch');
  const posFilter = document.getElementById('playerPosFilter');
  const ownerFilter = document.getElementById('playerOwnerFilter');
  const tbody = document.getElementById('playerTbody');
  const countEl = document.getElementById('playerCount');

  const positions = Array.from(new Set(PLAYER_SUCCESS.map(p => p.position))).sort();
  positions.forEach(pos => {
    const opt = document.createElement('option');
    opt.value = pos; opt.textContent = pos;
    posFilter.appendChild(opt);
  });

  const owners = Array.from(new Set(PLAYER_SUCCESS.map(p => p.best_team_owner))).sort();
  owners.forEach(o => {
    const opt = document.createElement('option');
    opt.value = o; opt.textContent = o;
    ownerFilter.appendChild(opt);
  });

  let sortKey = 'best_team_started_points';
  let sortDir = -1; // desc
  let expandedPlayer = null;

  function fmt(n) { return (n ?? 0).toFixed(2); }

  function renderDetailRows(p) {
    const rows = p.teams.map(t => `
      <tr>
        <td>${t.owner}</td>
        <td class="gg-num">${fmt(t.started_points)}</td>
        <td class="gg-num">${t.started_games}</td>
        <td class="gg-num">${fmt(t.bench_points)}</td>
        <td class="gg-num">${t.bench_games}</td>
        <td class="gg-num">${fmt(t.total_points)}</td>
      </tr>`).join('');
    return `
      <tr class="gg-player-detail-row">
        <td colspan="7">
          <div class="gg-player-detail">
            <table>
              <thead>
                <tr>
                  <th>Manager</th>
                  <th class="gg-num">Started Pts</th>
                  <th class="gg-num">Started Gms</th>
                  <th class="gg-num">Bench Pts</th>
                  <th class="gg-num">Bench Gms</th>
                  <th class="gg-num">Total Pts</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </td>
      </tr>`;
  }

  function render() {
    const q = searchInput.value.trim().toLowerCase();
    const pos = posFilter.value;
    const owner = ownerFilter.value;

    let filtered = PLAYER_SUCCESS.filter(p => {
      if (q && !p.player.toLowerCase().includes(q)) return false;
      if (pos !== 'all' && p.position !== pos) return false;
      if (owner !== 'all' && !p.teams.some(t => t.owner === owner)) return false;
      return true;
    });

    // When filtering to one manager, sort/display that manager's own numbers
    // for each player instead of the player's all-time best team — otherwise
    // a player who did great elsewhere but only okay here looks mismatched.
    const teamHeader = document.getElementById('colTeamHeader');
    const ptsHeader = document.getElementById('colPtsHeader');
    const gmsHeader = document.getElementById('colGmsHeader');
    if (owner !== 'all') {
      teamHeader.textContent = 'Team';
      ptsHeader.textContent = `Pts (w/ ${owner})`;
      gmsHeader.textContent = `Gms (w/ ${owner})`;
    } else {
      teamHeader.textContent = 'Best Team';
      ptsHeader.textContent = 'Pts (best team)';
      gmsHeader.textContent = 'Gms (best team)';
    }

    function displayTeam(p) {
      if (owner !== 'all') {
        const t = p.teams.find(t => t.owner === owner);
        return t ? { owner, points: t.started_points, games: t.started_games } : { owner, points: 0, games: 0 };
      }
      return { owner: p.best_team_owner, points: p.best_team_started_points, games: p.best_team_started_games };
    }

    filtered.sort((a, b) => {
      if (owner !== 'all' && (sortKey === 'best_team_started_points' || sortKey === 'best_team_started_games')) {
        const key = sortKey === 'best_team_started_points' ? 'points' : 'games';
        const av = displayTeam(a)[key], bv = displayTeam(b)[key];
        return sortDir * (av - bv);
      }
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === 'string') return sortDir * av.localeCompare(bv);
      return sortDir * ((av ?? 0) - (bv ?? 0));
    });

    countEl.textContent = `Showing ${filtered.length} of ${PLAYER_SUCCESS.length} players`;

    const rows = filtered.slice(0, 200).map(p => {
      const disp = displayTeam(p);
      const rowHtml = `
        <tr class="gg-player-row" data-player="${p.player.replace(/"/g, '&quot;')}">
          <td>${p.player}</td>
          <td><span class="gg-pos-tag">${p.position}</span></td>
          <td>${disp.owner}</td>
          <td class="gg-num" style="color:var(--amber);font-weight:700;">${fmt(disp.points)}</td>
          <td class="gg-num">${disp.games}</td>
          <td class="gg-num">${fmt(p.overall_started_points)}</td>
          <td class="gg-num">${fmt(p.overall_bench_points)}</td>
        </tr>`;
      if (expandedPlayer === p.player) {
        return rowHtml + renderDetailRows(p);
      }
      return rowHtml;
    }).join('');

    tbody.innerHTML = rows;

    tbody.querySelectorAll('tr.gg-player-row').forEach(row => {
      row.addEventListener('click', () => {
        const name = row.getAttribute('data-player');
        expandedPlayer = (expandedPlayer === name) ? null : name;
        render();
      });
    });
  }

  document.querySelectorAll('.gg-sort-th').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-sort');
      if (sortKey === key) {
        sortDir *= -1;
      } else {
        sortKey = key;
        sortDir = (key === 'player' || key === 'position' || key === 'best_team_owner') ? 1 : -1;
      }
      render();
    });
  });

  searchInput.addEventListener('input', render);
  posFilter.addEventListener('change', render);
  ownerFilter.addEventListener('change', render);

  render();
})();
