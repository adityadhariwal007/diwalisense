// Checks model access only; never prints the key or sends a chat/generation request.
const key = process.env.GEMINI_API_KEY;
const model = process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite';
if (!key) { console.error('Add GEMINI_API_KEY to frontend/.env.local, then retry.'); process.exitCode = 1; }
else if (!['gemini-3.5-flash-lite', 'gemini-3.8-flash'].includes(model)) { console.error('Choose a documented Flash model. No automatic fallback is enabled.'); process.exitCode = 1; }
else {
  try {
    const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000', { headers: { 'x-goog-api-key': key }, signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error();
    const data = await response.json();
    const available = (data.models || []).filter(item => /flash/.test(item.name) && item.supportedGenerationMethods?.includes('generateContent'));
    console.log('Flash models reported by this API project:', available.map(item => item.name.replace('models/', '')).join(', ') || 'none');
    if (!available.some(item => item.name === `models/${model}`)) { console.error('The selected model is unavailable. Do not upgrade billing or switch models automatically.'); process.exitCode = 1; }
    else console.log(`Selected model is accessible: ${model}. Confirm Free tier in AI Studio before using chat.`);
  } catch { console.error('Could not check model access. Check your API key and connection in Google AI Studio.'); process.exitCode = 1; }
}
