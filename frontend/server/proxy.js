/* Optional Node proxy: browser -> :3001/api -> FastAPI :8000 */
import express from 'express';
import cors from 'cors';
import { createProxyMiddleware } from 'http-proxy-middleware';

const PORT = process.env.PORT || 3001;
const app = express();

app.use(cors({ origin: 'http://localhost:5173' }));
/* pathFilter keeps the /api prefix intact when forwarding */
app.use(createProxyMiddleware({ target: 'http://localhost:8000', changeOrigin: true, pathFilter: '/api' }));

app.listen(PORT, () => console.log(`DocuSense proxy on :${PORT} -> http://localhost:8000`));
