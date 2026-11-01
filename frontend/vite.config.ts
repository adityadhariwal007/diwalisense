import { defineConfig, loadEnv } from 'vite';
import { createHandler } from './api/chat.mjs';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env };
  return {
  plugins: [react(), tailwindcss(), {
    name: 'local-chat-server',
    configureServer(server) {
      const handler = createHandler({ env });
      server.middlewares.use('/api/chat', (req, res) => { void handler(req, res); });
    },
  }],
  server: { proxy: { '/api': { target: 'http://127.0.0.1:8000', rewrite: path => path.replace(/^\/api/, '') } } },
  };
});
