export function clock(second) { return `${Math.floor(second / 60).toString().padStart(2, '0')}:${Math.floor(second % 60).toString().padStart(2, '0')}`; }
export function eventsAt(events, second) { return events.filter(e => e.match_second <= second); }
export function frameAt(frames, second) {
  let lo = 0, hi = frames.length - 1;
  while (lo < hi) { const mid = Math.ceil((lo + hi) / 2); if (frames[mid].match_second <= second) lo = mid; else hi = mid - 1; }
  return frames[lo];
}
export function statsAt(events, second) {
  const visible = eventsAt(events, second);
  return ['BLU', 'RED'].map(team_id => {
    const own = visible.filter(e => e.team_id === team_id);
    const passes = own.filter(e => e.event_type === 'pass');
    const complete = own.filter(e => e.event_type === 'pass_complete').length;
    const shots = own.filter(e => e.event_type === 'shot');
    return {team_id, pass_attempts:passes.length, pass_completions:complete, pass_completion_pct:passes.length ? complete / passes.length * 100 : 0, shots:shots.length, goals:own.filter(e => e.event_type === 'goal').length, xg:shots.reduce((sum,e) => sum + (e.xg || 0),0)};
  });
}
export function pressureWindows(events, second) {
  return Array.from({length:18}, (_, i) => {
    const start = i * 300;
    const passes = events.filter(e => e.event_type === 'pass' && e.match_second >= start && e.match_second < start + 300 && e.match_second <= second);
    return {start, available:start <= second, BLU:average(passes.filter(e => e.team_id === 'BLU')), RED:average(passes.filter(e => e.team_id === 'RED'))};
  });
}
function average(events) { const measured = events.filter(e => typeof e.pressure === 'number'); return measured.length ? measured.reduce((s,e) => s + e.pressure,0) / measured.length : 0; }
export function validateConnection(url, runId) {
  if (!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(runId)) return 'Enter a valid replay run UUID.';
  if (url !== '/fsi-api') { try { if (!['http:', 'https:'].includes(new URL(url).protocol)) return 'Use an HTTP or HTTPS API URL.'; } catch { return 'Enter an absolute API URL or /fsi-api.'; } }
  return '';
}
