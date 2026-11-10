# DocuSense AI Frontend
React 18 + Vite, plain CSS, anime.js 3.
```
npm install
npm run dev      # :5173, /api proxied to FastAPI :8000 (vite.config.js)
npm start        # optional: also runs Node proxy on :3001
```
Backend: `uvicorn app.main:app --reload` (port 8000).
