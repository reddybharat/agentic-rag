# Frontend

React + Vite + Tailwind + shadcn/ui. Needs the backend running (see [../backend/README.md](../backend/README.md)).

```
cp .env.example .env   # optional; VITE_API_URL defaults to http://localhost:8000
npm install
npm run dev            # http://localhost:5173
npm run build          # type-check + production build
npm run lint
```

Add shadcn components with `npx shadcn@latest add <name>`.
