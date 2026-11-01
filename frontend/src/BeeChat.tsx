import { useEffect, useRef, useState, type FormEvent } from 'react';
import './styles/chat.css';

type Message = { role: 'user' | 'assistant'; text: string; links?: { label: string; href: string }[] };
const safePaths = new Set(['/#compare', '/#guidelines', '/#data']);
export function parseChatReply(value: unknown): Message {
  const data = value as { answer?: unknown; links?: unknown } | null;
  if (!data || typeof data.answer !== 'string' || !data.answer.trim() || data.answer.length > 3000 || !Array.isArray(data.links)) throw new Error('Buzzy could not read that answer. Please try again.');
  const links = data.links.filter((link): link is { label: string; href: string } => !!link && typeof link === 'object' && typeof link.label === 'string' && link.label.length <= 100 && typeof link.href === 'string' && safePaths.has(link.href)).slice(0, 3);
  return { role: 'assistant', text: data.answer, links };
}
export function ChatMessage({ message }: { message: Message }) {
  return <div className={`bee-message bee-message-${message.role}`}><span className="bee-speaker">{message.role === 'user' ? 'You' : 'Buzzy'}</span><p>{message.text}</p>{!!message.links?.length && <div className="bee-message-links">{message.links.filter(link => safePaths.has(link.href)).map(link => <a key={link.href} href={link.href}>{link.label}</a>)}</div>}</div>;
}

export default function BeeChat({ area }: { area?: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [motion, setMotion] = useState(true);
  const [retryAt, setRetryAt] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const panel = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const retryButton = useRef<HTMLButtonElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const request = useRef<AbortController | null>(null);
  const locked = useRef(false);
  const wasOpened = useRef(false);
  const waitSeconds = Math.max(0, Math.ceil((retryAt - clock) / 1000));
  const full = messages.length >= 16;

  useEffect(() => {
    if (open) { wasOpened.current = true; panel.current?.show(); input.current?.focus(); }
    else { panel.current?.close(); if (wasOpened.current) launcher.current?.focus(); }
  }, [open]);
  useEffect(() => {
    if (open && !busy) (messages.at(-1)?.role === 'user' ? retryButton.current : input.current)?.focus();
  }, [open, busy, messages]);
  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); setOpen(false); } };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, [open]);
  useEffect(() => { history.current?.scrollTo({ top: history.current.scrollHeight, behavior: 'instant' }); }, [messages, busy, error]);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!retryAt) return;
    const timer = setInterval(() => { const now = Date.now(); setClock(now); if (now >= retryAt) setRetryAt(0); }, 1000);
    return () => clearInterval(timer);
  }, [retryAt]);
  const close = () => { setOpen(false); };
  const reset = () => { request.current?.abort(); request.current = null; locked.current = false; setMessages([]); setDraft(''); setError(''); setBusy(false); input.current?.focus(); };
  const send = async (conversation: Message[]) => {
    if (locked.current || Date.now() < retryAt) return;
    locked.current = true; setBusy(true); setError('');
    const controller = new AbortController(); request.current = controller;
    const timer = setTimeout(() => controller.abort(), 35_000);
    try {
      const response = await fetch('/api/chat', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: conversation.map(({ role, text }) => ({ role, text })), ...(area && area !== 'Your location' ? { area } : {}) }), signal: controller.signal });
      const data = await response.json().catch(() => { throw new Error('Buzzy could not connect. Please try again.'); });
      if (request.current !== controller) return;
      if (!response.ok) {
        if (response.status === 429) { const seconds = Math.min(86400, Math.max(1, Number(response.headers.get('Retry-After')) || 60)); setClock(Date.now()); setRetryAt(Date.now() + seconds * 1000); }
        throw new Error(typeof data?.error === 'string' ? data.error : 'Buzzy could not connect. Please try again.');
      }
      setMessages([...conversation, parseChatReply(data)]);
    } catch (reason) {
      if (request.current === controller) setError(reason instanceof Error && reason.name === 'Error' ? reason.message : reason instanceof Error && reason.name === 'AbortError' ? 'The reply took too long. Please try again.' : 'Buzzy could not connect. Please try again.');
    } finally {
      clearTimeout(timer);
      if (request.current === controller) { locked.current = false; setBusy(false); request.current = null; }
    }
  };
  const ask = (text: string) => {
    if (!text.trim() || busy || full || messages.at(-1)?.role === 'user' || waitSeconds) return;
    const next = [...messages, { role: 'user' as const, text: text.trim().slice(0, 1000) }];
    setMessages(next); setDraft(''); void send(next);
  };
  const submit = (event: FormEvent) => { event.preventDefault(); ask(draft); };
  const pending = messages.at(-1)?.role === 'user';

  return <>
    <button ref={launcher} className={`bee-chat-launcher ${motion ? '' : 'bee-still'}`} aria-label="Ask Buzzy, your AI air guide" aria-expanded={open} aria-controls="bee-chat" onClick={() => setOpen(value => !value)} hidden={open}>
      <span className="bee-launcher-label">Ask Buzzy<span>Your air guide</span></span><span className="bee-flight"><img src="/bee-guide.jpeg" alt="" width="86" height="86" /></span>
    </button>
    <dialog ref={panel} id="bee-chat" className={`bee-chat-panel ${motion ? '' : 'bee-still'}`} aria-labelledby="bee-title" onCancel={event => { event.preventDefault(); close(); }}>
      <header className="bee-chat-header"><span className="bee-avatar"><img src="/bee-guide.jpeg" alt="" width="60" height="60" /></span><div><h2 id="bee-title">Hi, I’m Buzzy.</h2><p>Your AI air guide</p></div><button className="bee-close" onClick={close} aria-label="Close chat">×</button></header>
      <div className="bee-chat-controls"><button onClick={reset}>New chat</button><button aria-pressed={!motion} onClick={() => setMotion(value => !value)}>{motion ? 'Pause bee' : 'Animate bee'}</button></div>
      <div ref={history} className="bee-chat-history" role="log" aria-label="Chat messages" aria-live="polite" aria-relevant="additions text">
        {!messages.length && <div className="bee-welcome"><p>I can explain the Diwali air data or help you choose a purifier size.</p><p>English, Hindi or Hinglish—all welcome.</p><div className="bee-prompts">{['Explain the air near my area', 'Help me choose an air purifier', 'What can students do?'].map(text => <button key={text} onClick={() => ask(text)}>{text}</button>)}</div></div>}
        {messages.map((message, index) => <ChatMessage key={index} message={message} />)}
        {busy && <p className="bee-status" role="status"><span className="bee-dots" aria-hidden="true">● ● ●</span> Buzzy is thinking…</p>}
        {error && <div className="bee-error" role="alert"><p>{error}</p><button ref={retryButton} disabled={busy || waitSeconds > 0} onClick={() => void send(messages)}>{waitSeconds ? `Try again in ${waitSeconds}s` : 'Retry reply'}</button><button onClick={() => { const last = messages.at(-1); if (last?.role === 'user') { setDraft(last.text); setMessages(messages.slice(0, -1)); setError(''); } }}>Edit question</button><a href="/#guidelines">Read the guidance</a></div>}
        {full && <p className="bee-status">That’s 8 questions. Start a new chat to continue.</p>}
      </div>
      <p className="bee-privacy">Messages go to Google Gemini. Don’t share private details. This app keeps chat only until you reload.</p>
      <form className="bee-chat-form" onSubmit={submit}><label htmlFor="bee-question">Ask about the air</label><div><textarea ref={input} id="bee-question" value={draft} onChange={event => setDraft(event.target.value)} maxLength={1000} rows={2} placeholder="Ask Buzzy…" disabled={busy || full || pending || waitSeconds > 0} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); ask(draft); } }} /><button type="submit" disabled={busy || full || pending || waitSeconds > 0 || !draft.trim()} aria-label="Send message">↑</button></div></form>
    </dialog>
  </>;
}
