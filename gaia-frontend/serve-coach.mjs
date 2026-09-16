// Separate local viewer: no change to the existing live replay server or game server.
import { createServer } from 'vite';
const port = Number(process.env.COACH_UI_PORT || 5174);
const api = Number(process.env.COACH_API_PORT || 8789);
const server = await createServer({
  server: { host: '127.0.0.1', port, strictPort: true,
    proxy: { '/coach-api': `http://127.0.0.1:${api}` } },
});
await server.listen();
server.printUrls();
