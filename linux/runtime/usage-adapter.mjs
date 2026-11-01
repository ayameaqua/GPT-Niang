// Linux-only transport/lifecycle layer. Shared query and account semantics stay upstream.
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {readUsage, freshness} from '../../gpt-niang-usage/runtime/usage.mjs';
import {createRefreshQueue, mergeUsageSnapshot} from '../../gpt-niang-usage/runtime/refresh-queue.mjs';

export const MAX_LINE = 64 * 1024;
const VERSION = 1;

export function publicSnapshot(snapshot, now = Date.now()) {
  if (!snapshot) return null;
  const fields = ['ok', 'queryOk', 'observedAt', 'checkedAt', 'plan', 'planLabel', 'accountVerified', 'error', 'errorCode'];
  const result = Object.fromEntries(fields.filter(key => snapshot[key] !== undefined).map(key => [key, snapshot[key]]));
  result.windows = (snapshot.windows ?? []).map(window => ({...window, freshness: freshness(window, snapshot.observedAt, now)}));
  // Account fingerprints are only needed inside this process, never by the UI or logs.
  return result;
}

export function createAdapter({query = readUsage, send, spawnProcess = spawn, now = Date.now,
  timeoutMs = 18000, fallbackTimeoutMs = 10000, cleanupMs = 600} = {}) {
  let snapshot = null, latest = null, closing = false;
  const children = new Set();
  const timers = new Set();
  const emit = (type, requestId, extra = {}) => send({schemaVersion: VERSION, type, requestId, ...extra});
  async function reapChildren() {
    const owned = [...children];
    if (!owned.length) return;
    for (const child of owned) {try {child.stdin?.end(); child.kill('SIGTERM');} catch {}}
    let timer;
    await Promise.race([
      Promise.all(owned.map(child => new Promise(resolve => {
        if (!children.has(child)) return resolve();
        child.once('close', resolve);
      }))),
      new Promise(resolve => {timer = setTimeout(resolve, cleanupMs);})
    ]);
    clearTimeout(timer);
    for (const child of owned) if (children.has(child)) {try {child.kill('SIGKILL');} catch {}}
  }
  const trackSpawn = (...args) => {
    const child = spawnProcess(...args);
    children.add(child);
    child.once('close', () => children.delete(child));
    // readUsage sends TERM after each query; bound the lifetime of uncooperative CLIs.
    child.once('spawn', () => {
      const deadline = setTimeout(() => {child.kill('SIGKILL'); timers.delete(deadline);}, timeoutMs + fallbackTimeoutMs + cleanupMs);
      timers.add(deadline);
      child.once('close', () => {clearTimeout(deadline); timers.delete(deadline);});
    });
    return child;
  };
  const queue = createRefreshQueue(async () => {
    if (closing) return;
    const request = latest;
    emit('refreshing', request.requestId);
    const next = await query(request.codexPath, {timeoutMs, fallbackTimeoutMs, spawnProcess: trackSpawn,
      onAccount(key) {
        if (snapshot && (!key || key !== snapshot.accountKey)) {
          snapshot = null;
          emit('snapshot', request.requestId, {data: null});
        }
      }});
    await reapChildren();
    if (closing) return;
    snapshot = mergeUsageSnapshot(snapshot, next, now());
    emit('snapshot', request.requestId, {data: publicSnapshot(snapshot, now())});
  }, {onError: () => {
    snapshot = null;
    emit('error', latest?.requestId ?? null, {code: 'QUERY_FAILED', message: '额度查询失败，请重试'});
  }});

  async function shutdown(requestId = null) {
    if (closing) return;
    closing = true;
    await reapChildren();
    for (const timer of timers) clearTimeout(timer);
    timers.clear();
    emit('shutdown', requestId);
  }

  function receive(message) {
    if (closing) return;
    if (!message || typeof message !== 'object' || Array.isArray(message) || message.schemaVersion !== VERSION ||
        typeof message.requestId !== 'string' || !message.requestId || message.requestId.length > 64) {
      emit('error', null, {code: 'BAD_MESSAGE', message: '无效的协议消息'});
      return;
    }
    if (message.type === 'shutdown') return shutdown(message.requestId);
    if (message.type !== 'refresh' || typeof message.codexPath !== 'string' || !message.codexPath.startsWith('/') ||
        message.codexPath.length > 4096 || message.codexPath.includes('\0')) {
      emit('error', message.requestId, {code: 'BAD_REQUEST', message: '无效的刷新请求'});
      return;
    }
    latest = message;
    return queue.request();
  }
  return {receive, shutdown, get busy() {return queue.busy;}};
}

export function serve({input = process.stdin, output = process.stdout} = {}) {
  let buffer = Buffer.alloc(0), ending = false;
  const adapter = createAdapter({send: message => {
    if (!output.destroyed) output.write(JSON.stringify(message) + '\n');
  }});
  const finish = async () => {
    if (ending) return;
    ending = true;
    input.pause();
    await adapter.shutdown();
    process.exit(0);
  };
  input.on('data', chunk => {
    buffer = Buffer.concat([buffer, chunk]);
    let newline;
    while ((newline = buffer.indexOf(10)) >= 0) {
      if (newline > MAX_LINE) return void finish();
      const line = buffer.subarray(0, newline);
      buffer = buffer.subarray(newline + 1);
      if (!line.length) continue;
      try {
        const message = JSON.parse(line.toString('utf8'));
        if (message?.type === 'shutdown' && message.schemaVersion === VERSION && typeof message.requestId === 'string' && message.requestId.length <= 64) {
          void adapter.receive(message).then(finish);
        } else void adapter.receive(message);
      } catch {
        output.write(JSON.stringify({schemaVersion: VERSION, type: 'error', requestId: null, code: 'BAD_JSON', message: '协议 JSON 无效'}) + '\n');
      }
    }
    if (buffer.length > MAX_LINE) void finish();
  });
  input.on('end', finish);
  input.on('error', finish);
  output.on('error', finish);
  process.on('SIGTERM', finish);
  process.on('SIGINT', finish);
  // stdin EOF normally handles a killed GUI. This also covers inherited pipe handles.
  const parent = process.ppid;
  setInterval(() => {if (process.ppid !== parent || process.ppid === 1) void finish();}, 1000).unref();
  return adapter;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) serve();
