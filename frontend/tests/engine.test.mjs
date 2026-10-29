import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {eventsAt,frameAt,statsAt,pressureWindows,validateConnection} from '../src/engine.mjs';
const replay=JSON.parse(await readFile(new URL('../public/data/replay.json',import.meta.url),'utf8'));
test('replay cutoffs never reveal future events or frames',()=>{
 for(const second of [0,2.4,599,2700,3840,5400]){
  assert.ok(eventsAt(replay.events,second).every(e=>e.match_second<=second));
  const frame=frameAt(replay.frames,second);assert.ok(frame.match_second<=second);
  assert.equal(frame.match_second,Math.max(...replay.frames.filter(f=>f.match_second<=second).map(f=>f.match_second)));
 }
});
test('passing and xG use distinct canonical event records',()=>{
 const events=[{team_id:'BLU',event_type:'pass',match_second:1},{team_id:'BLU',event_type:'pass_complete',match_second:2},{team_id:'BLU',event_type:'pass',match_second:3},{team_id:'BLU',event_type:'shot',match_second:4,xg:.3},{team_id:'BLU',event_type:'goal',match_second:4.1,xg:.3}];
 assert.deepEqual(statsAt(events,4.1)[0],{team_id:'BLU',pass_attempts:2,pass_completions:1,pass_completion_pct:50,shots:1,goals:1,xg:.3});
 assert.equal(statsAt(events,1)[0].pass_completions,0);
});
test('pressure windows exclude future and missing measurements',()=>{
 const windows=pressureWindows([{event_type:'pass',team_id:'BLU',match_second:20,pressure:.6},{event_type:'pass',team_id:'BLU',match_second:21,pressure:null},{event_type:'pass',team_id:'BLU',match_second:100,pressure:1}],50);
 assert.equal(windows[0].BLU,.6);assert.equal(windows[1].available,false);
});
test('API configuration rejects invalid runs and unsafe schemes',()=>{
 assert.equal(validateConnection('/fsi-api',replay.runId),'');
 assert.equal(validateConnection('https://example.com',replay.runId),'');
 assert.ok(validateConnection('javascript:alert(1)',replay.runId));
 assert.ok(validateConnection('/fsi-api','not-a-uuid'));
});
