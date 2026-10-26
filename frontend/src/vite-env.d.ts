/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEMO_SELLER_ORGANIZATION_ID?: string;
  readonly VITE_ENABLE_DEMO_QUICK_FILL?: string;
  readonly VITE_APP_ENV?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
