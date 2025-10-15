type ServiceKey =
  | "VITE_API_CLIENTES_URL"
  | "VITE_API_INSTALACIONES_URL"
  | "VITE_API_TICKETS_URL"
  | "VITE_API_RED_URL"
  | "VITE_API_INVENTARIO_URL";

const FALLBACK: Record<ServiceKey, string> = {
  VITE_API_CLIENTES_URL: "http://localhost:8000",
  VITE_API_INSTALACIONES_URL: "http://localhost:8005",
  VITE_API_TICKETS_URL: "http://localhost:8006",
  VITE_API_RED_URL: "http://localhost:8020",
  VITE_API_INVENTARIO_URL: "http://localhost:8008"
};

const cache = new Map<ServiceKey, string>();

export function getServiceUrl(key: ServiceKey): string {
  if (cache.has(key)) return cache.get(key)!;
  const runtime = window.__ENV__?.[key];
  const injected = import.meta.env[key];
  const value = runtime || injected || FALLBACK[key];
  cache.set(key, value);
  return value;
}
