interface Window {
  __ENV__?: Record<string, string>;
}

interface ImportMetaEnv {
  readonly VITE_API_CLIENTES_URL?: string;
  readonly VITE_API_FACTURACION_URL?: string;
  readonly VITE_API_PAGOS_URL?: string;
  readonly VITE_API_ORQUESTADOR_URL?: string;
  readonly VITE_API_INSTALACIONES_URL?: string;
  readonly VITE_API_RED_URL?: string;
  readonly VITE_API_TICKETS_URL?: string;
  readonly VITE_API_REPORTES_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
