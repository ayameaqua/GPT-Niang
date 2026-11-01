import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';
import {createAdapter, publicSnapshot} from '../runtime/usage-adapter.mjs';

const request = id => ({schemaVersion: 1, type: 'refresh', requestId: String(id), codexPath: '/fake/codex'});
const good = (key = 'one') => ({ok: true, queryOk: true, observedAt: Date.now(), accountKey: key, planLabel: 'Pro',
  windows: [{label: '每周', minutes: 10080, remaining: 40, used: 60, resetsAt: null}]});

test('concurrent refreshes run at most one query plus one follow-up', async () => {
  const output = [], releases = [];
  let active = 0, maximum = 0, calls = 0;
  const adapter = createAdapter({send: m => output.push(m), query: async () => {
    calls++; active++; maximum = Math.max(maximum, active);
    await new Promise(resolve => releases.push(resolve));
    active--; return good();
  }});
  const done = adapter.receive(request(1));
  adapter.receive(request(2)); adapter.receive(request(3)); adapter.receive(request(4));
  releases.shift()();
  await new Promise(resolve => setImmediate(resolve));
  releases.shift()();
  await done;
  assert.equal(calls, 2); assert.equal(maximum, 1);
  assert.deepEqual(output.filter(m => m.type === 'snapshot').map(m => m.requestId), ['1', '4']);
  await adapter.shutdown();
});

test('same-account failure retains successful timestamp; account change clears before query finishes', async () => {
  const output = [];
  let count = 0;
  const first = good();
  const adapter = createAdapter({send: m => output.push(m), query: async (_, {onAccount}) => {
    count++;
    if (count === 1) return first;
    if (count === 2) {onAccount('one'); return {ok: false, queryOk: false, accountKey: 'one', clearPrevious: false, error: 'offline'};}
    onAccount('two');
    assert.equal(output.at(-1).data, null);
    return {...good('two'), ok: false, queryOk: false, windows: [], clearPrevious: false};
  }});
  await adapter.receive(request(1)); await adapter.receive(request(2));
  assert.equal(output.at(-1).data.observedAt, first.observedAt);
  assert.equal(output.at(-1).data.queryOk, false);
  assert.equal(output.at(-1).data.windows.length, 1);
  await adapter.receive(request(3));
  assert.equal(output.at(-1).data.windows.length, 0);
  await adapter.shutdown();
});

test('zero windows and any number of actual windows pass through without inventing data', () => {
  assert.deepEqual(publicSnapshot({...good(), windows: []}).windows, []);
  const data = publicSnapshot({...good(), windows: [
    {label: '个人额度', minutes: null, remaining: 0, resetsAt: null},
    {label: '5 小时', minutes: 300, remaining: 100, resetsAt: 1},
    {label: '每周', minutes: 10080, remaining: 9, resetsAt: null}]
  });
  assert.equal(data.windows.length, 3);
  assert.equal(data.windows[1].freshness, 'expired');
  assert.equal(data.windows[0].remaining, 0);
  assert.equal('accountKey' in data, false);
});

test('invalid envelopes cannot start a query', async () => {
  const output = [];
  const adapter = createAdapter({send: m => output.push(m), query: () => assert.fail('query must not run')});
  for (const message of [null, [], {}, {...request(1), schemaVersion: 2}, {...request(1), codexPath: 'relative'}, {...request(1), type: 'turn/start'}]) adapter.receive(message);
  assert.equal(output.length, 6);
  assert.ok(output.every(m => m.type === 'error'));
  await adapter.shutdown();
});

test('EOF cleans an uncooperative app-server and exits without a worker socket', {timeout: 8000}, async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pet lifecycle '));
  const cli = path.join(root, 'codex');
  const pidfile = path.join(root, 'pid');
  fs.writeFileSync(cli, `#!${process.execPath}\nimport fs from 'node:fs';\nfs.writeFileSync(${JSON.stringify(pidfile)}, String(process.pid));\nprocess.on('SIGTERM',()=>{});\nsetInterval(()=>{},100);\n`);
  fs.chmodSync(cli, 0o755);
  const adapter = fileURLToPath(new URL('../runtime/usage-adapter.mjs', import.meta.url));
  const child = spawn(process.execPath, [adapter], {stdio: ['pipe', 'pipe', 'pipe']});
  t.after(() => {child.kill('SIGKILL'); fs.rmSync(root, {recursive: true, force: true});});
  const output = [];
  child.stdout.on('data', data => output.push(data.toString()));
  child.stdin.write(JSON.stringify({...request(1), codexPath: cli}) + '\n');
  for (let n = 0; !fs.existsSync(pidfile) && n < 100; n++) await new Promise(r => setTimeout(r, 20));
  assert.ok(fs.existsSync(pidfile));
  const pid = Number(fs.readFileSync(pidfile, 'utf8'));
  child.stdin.end();
  const [code] = await once(child, 'exit');
  assert.equal(code, 0);
  for (let n = 0; n < 30; n++) {
    try {process.kill(pid, 0);} catch {return;}
    await new Promise(r => setTimeout(r, 20));
  }
  assert.fail('app-server survived worker EOF');
});
