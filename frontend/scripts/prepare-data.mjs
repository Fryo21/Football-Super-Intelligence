// Read-only import of a repository replay. All generated files stay in frontend.
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root = new URL('../../', import.meta.url);
const runId = '426b7bce-2df0-47fc-b50f-16eb35a094db';
const source = new URL(`data/runtime/matches/${runId}/`, root);
const read = async name => JSON.parse(await readFile(new URL(name, source), 'utf8'));
const [metadata, events, frames] = await Promise.all(['canonical_metadata.json','canonical_events.json','canonical_frames.json'].map(read));
const sampled = frames.filter((frame, index) => index === 0 || index === frames.length - 1 || frame.match_second % 5 === 0);
const output = new URL('../public/data/', import.meta.url);
await mkdir(output, {recursive:true});
await writeFile(new URL('replay.json', output), JSON.stringify({runId, metadata, events, frames:sampled}));
console.log(`Imported ${events.length} events and ${sampled.length} tracking frames to ${fileURLToPath(output)}`);
