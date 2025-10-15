type ServiceKey =
  | "VITE_API_CLIENTES_URL"
  | "VITE_API_FACTURACION_URL"
  | "VITE_API_PAGOS_URL"
  | "VITE_API_ORQUESTADOR_URL"
  | "VITE_API_INSTALACIONES_URL"
  | "VITE_API_RED_URL"
  | "VITE_API_TICKETS_URL"
  | "VITE_API_REPORTES_URL"
  | "VITE_ROUTER_SIM_URL";

const FALLBACK: Record<ServiceKey, string> = {
  VITE_API_CLIENTES_URL: "http://localhost:8000",
  VITE_API_FACTURACION_URL: "http://localhost:8002",
  VITE_API_PAGOS_URL: "http://localhost:8003",
  VITE_API_ORQUESTADOR_URL: "http://localhost:8010",
  VITE_API_INSTALACIONES_URL: "http://localhost:8005",
  VITE_API_RED_URL: "http://localhost:8020",
  VITE_API_TICKETS_URL: "http://localhost:8006",
  VITE_API_REPORTES_URL: "http://localhost:8007",
  VITE_ROUTER_SIM_URL: "http://localhost:8100"
};

const cache = new Map<ServiceKey, string>();

export function getServiceUrl(key: ServiceKey): string {
  if (cache.has(key)) {
    return cache.get(key)!;
  }
  const runtime = window.__ENV__?.[key];
  const imported = import.meta.env[key];
  const value = runtime || imported || FALLBACK[key];
  cache.set(key, value);
  return value;
}
