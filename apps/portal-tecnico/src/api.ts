import axios, { AxiosInstance } from "axios";
import { getServiceUrl } from "./config";

export interface InstalacionRow {
  id: number;
  clienteId: number;
  estado: string;
  ventana: string;
  zona: string;
  notas: string;
  evidencias: string[];
  creadoEn: string;
}

export interface TicketRow {
  id: number;
  tipo: string;
  prioridad: string;
  estado: string;
  zona: string;
  clienteId: number;
  asignadoA: string;
  slaAt: string;
}

export interface RouterPing {
  host: string;
  ok: boolean;
  latency_ms: number;
  estado?: {
    cliente_id: number;
    conectado: boolean;
    latencia_ms: number;
    ip_fake?: string;
    actualizado_en: string;
  };
}

export interface RouterLogEntry {
  timestamp: string;
  message: string;
}

export interface RouterSummary {
  router_id: string;
  cliente_id?: number;
  state: "on" | "off";
  ip: string;
  uptime: number;
  last_state_change: string;
  logs: RouterLogEntry[];
}

export type RouterPowerAction = "on" | "off" | "reboot";

const cache: Record<string, AxiosInstance> = {};

function client(key: Parameters<typeof getServiceUrl>[0], timeout = 7000) {
  if (!cache[key]) {
    cache[key] = axios.create({ baseURL: getServiceUrl(key), timeout });
  }
  return cache[key];
}

export async function fetchAgenda(zona: string) {
  const http = client("VITE_API_INSTALACIONES_URL");
  const { data } = await http.get<InstalacionRow[]>("/instalaciones/agenda", { params: { zona } });
  return data;
}

export async function updateInstalacionEstado(
  id: number,
  estado: "EnRuta" | "Completada",
  evidencias?: string[],
  notas?: string
) {
  const http = client("VITE_API_INSTALACIONES_URL");
  if (estado === "EnRuta") {
    const { data } = await http.put(`/instalaciones/despachar/${id}`);
    return data;
  }
  const payload = { evidencias: evidencias?.length ? evidencias : ["sin-evidencias"], notas: notas ?? "" };
  const { data } = await http.put(`/instalaciones/cerrar/${id}`, payload);
  return data;
}

export async function pingHost(host: string, clienteId?: number) {
  const http = client("VITE_API_RED_URL");
  const { data } = await http.post<RouterPing>("/diagnostico/ping", { host, cliente_id: clienteId });
  return data;
}

export async function traceroute(host: string) {
  const http = client("VITE_API_RED_URL");
  const { data } = await http.post<{ host: string; hops: string[] }>("/diagnostico/traceroute", { host });
  return data;
}

export async function fetchTickets(zona: string) {
  const http = client("VITE_API_TICKETS_URL");
  const { data } = await http.get<TicketRow[]>("/tickets", { params: { zona } });
  return data;
}

export async function marcarTicketResuelto(id: number) {
  const http = client("VITE_API_TICKETS_URL");
  const { data } = await http.put(`/tickets/${id}/estado`, { estado: "Resuelto" });
  return data;
}

export async function fetchInventario(zona: string) {
  const http = client("VITE_API_INVENTARIO_URL");
  const { data } = await http.get("/inventario/available", { params: { zona, items: "ONT:1,ROUTER:1" } });
  return data;
}

function mapRouter(raw: any): RouterSummary {
  return {
    router_id: raw?.router_id ?? raw?.id ?? "",
    cliente_id: raw?.cliente_id,
    state: raw?.state === "off" ? "off" : "on",
    ip: raw?.ip ?? "10.10.0.0",
    uptime: typeof raw?.uptime === "number" ? raw.uptime : 0,
    last_state_change: raw?.last_state_change ?? raw?.timestamp ?? new Date().toISOString(),
    logs: Array.isArray(raw?.logs)
      ? raw.logs.map((log: any) => ({
          timestamp: log?.timestamp ?? new Date().toISOString(),
          message: log?.message ?? String(log ?? "")
        }))
      : []
  };
}

export async function fetchRouters(): Promise<RouterSummary[]> {
  const http = client("VITE_ROUTER_SIM_URL");
  const { data } = await http.get("/routers");
  return Array.isArray(data) ? data.map(mapRouter) : [];
}

export async function controlRouter(routerId: string, action: RouterPowerAction): Promise<RouterSummary> {
  const http = client("VITE_ROUTER_SIM_URL");
  const { data } = await http.post(`/routers/${routerId}/power`, { action });
  return mapRouter(data);
}
