# SyncAlly web app

React and TypeScript client scaffold using Vite. The current page is a placeholder and is not connected to the API.

From this directory, install the locked dependencies and run the app:

```powershell
npm ci
npm run dev
```

Run the frontend render test, lint/type checks, and production build with:

```powershell
npm test
npm run lint:check
npm run build
```

Use feature-oriented folders under src/ as product flows are implemented. Keep API access in a shared client module and keep server-side authorization and business rules in the backend.
