import { ChatError, MAX_BYTES, replyToChat } from '../server/chat.mjs';

async function readBody(req) {
  const length = req.headers['content-length'];
  if (length !== undefined && (!/^\d+$/.test(length) || Number(length) > MAX_BYTES)) throw new ChatError(413, 'Message too large. Keep your question short.');
  if (req.body !== undefined) {
    const raw = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
    if (Buffer.byteLength(raw) > MAX_BYTES) throw new ChatError(413, 'Message too large. Keep your question short.');
    try { return JSON.parse(raw); } catch { throw new ChatError(400, 'Send a valid text message.'); }
  }
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    const cleanup = () => { clearTimeout(timer); req.off('data', data); req.off('end', end); req.off('error', error); };
    const error = () => { cleanup(); reject(new ChatError(400, 'The message could not be read.')); };
    const data = chunk => {
      size += chunk.length;
      if (size > MAX_BYTES) { cleanup(); req.resume(); reject(new ChatError(413, 'Message too large. Keep your question short.')); }
      else chunks.push(chunk);
    };
    const end = () => {
      cleanup();
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch { reject(new ChatError(400, 'Send a valid text message.')); }
    };
    const timer = setTimeout(() => { cleanup(); req.resume(); reject(new ChatError(408, 'The message took too long to arrive. Try again.')); }, 3000);
    req.on('data', data); req.on('end', end); req.on('error', error);
  });
}

export function createHandler({ env = process.env, reply = replyToChat } = {}) {
  return async (req, res) => {
    res.setHeader('Cache-Control', 'no-store'); res.setHeader('Content-Type', 'application/json; charset=utf-8'); res.setHeader('X-Content-Type-Options', 'nosniff');
    try {
      if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); throw new ChatError(405, 'Use POST to send a chat message.'); }
      const allowed = (env.CHAT_ALLOWED_ORIGINS || (env.VERCEL ? 'https://diwalisense.vercel.app' : 'http://127.0.0.1:5173,http://localhost:5173')).split(',').map(value => value.trim());
      if (!allowed.includes(req.headers.origin) || req.headers['sec-fetch-site'] === 'cross-site') throw new ChatError(403, 'Open chat from the DiwaliSense website.');
      if (!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] || '')) throw new ChatError(415, 'Send a text message as JSON.');
      const body = await readBody(req);
      const identity = env.VERCEL ? String(req.headers['x-forwarded-for'] || 'unknown').split(',')[0].trim() : (req.socket?.remoteAddress || 'local');
      const result = await reply(body, { env, identity });
      res.statusCode = 200; res.end(JSON.stringify(result));
    } catch (error) {
      const known = error instanceof ChatError;
      res.statusCode = known ? error.status : 500;
      if (known && error.retryAfter) res.setHeader('Retry-After', String(error.retryAfter));
      res.end(JSON.stringify({ error: known ? error.message : 'The helper is unavailable. Please try again.' }));
    }
  };
}
export default createHandler();
