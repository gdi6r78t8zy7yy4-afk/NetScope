/// <reference types="vite/client" />

declare module 'react/jsx-runtime' {
  const namespace: any;
  export = namespace;
}

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module '*.css' {
  const classes: { [key: string]: string };
  export default classes;
}
