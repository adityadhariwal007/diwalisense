import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { transformWithOxc } from 'vite';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

test('chat renders model text as escaped text and rejects unsafe links', async () => {
  const source = (await readFile(new URL('../src/BeeChat.tsx', import.meta.url), 'utf8')).replace("import './styles/chat.css';", '');
  const compiled = await transformWithOxc(source, 'BeeChat.tsx', { jsx: { runtime: 'automatic' } });
  const require = createRequire(import.meta.url);
  const code = compiled.code.replace(/from ["'](react(?:\/jsx-runtime)?)["']/g, (_, name) => `from ${JSON.stringify(pathToFileURL(require.resolve(name)).href)}`);
  const { ChatMessage, parseChatReply } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
  for (const value of [null, {}, { answer: '', links: [] }, { answer: 'x'.repeat(3001), links: [] }, { answer: 'ok', links: null }]) assert.throws(() => parseChatReply(value), /could not read/);
  assert.deepEqual(parseChatReply({ answer: 'ok', links: [null, false, {}, { label: 'Bad', href: 'javascript:alert(1)' }, { label: 'Data', href: '/#data' }] }), { role: 'assistant', text: 'ok', links: [{ label: 'Data', href: '/#data' }] });
  const html = renderToStaticMarkup(createElement(ChatMessage, { message: { role: 'assistant', text: '<img src=x onerror=alert(1)><script>alert(1)</script>', links: [{ label: '<b>Data</b>', href: '/#data' }, { label: 'Bad', href: 'javascript:alert(1)' }, { label: 'External', href: 'https://evil.example' }] } }));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>') && !html.includes('<img src=x'));
  assert.ok(html.includes('href="/#data"') && html.includes('&lt;b&gt;Data&lt;/b&gt;'));
  assert.ok(!html.includes('javascript:') && !html.includes('https://evil.example'));
});
