import axios, { AxiosInstance } from "axios";
import { getServiceUrl } from "../config";

export interface ClientSummary {
  id: number;
  nombre: string;
  rfc: string;
  email: string;
  telefono: string;
  estatus: string;
  zona: string;
  plan_id?: string | null;
  router_id?: string | null;
}

export interface FacturaSummary {
  uuid: string;
  total: number;
  estatus: string;
  xml_path?: string;
}

export interface PagoSummary {
  referencia: string;
  metodo: string;
  monto: number;
  estatus: string;
  clienteId?: number | null;
  creadoEn?: string;
}

export interface TicketSummary {
  id: number;
  tipo: string;
  prioridad: string;
  estado: string;
  zona: string;
  clienteId: number;
  asignadoA: string;
  slaAt: string;
  creadoEn?: string;
}

export interface InstalacionSummary {
  id: number;
  clienteId: number;
  estado: string;
  ventana: string;
  zona: string;
  notas: string;
  evidencias: string[];
  creadoEn: string;
}

export interface RouterLogEntry {
  timestamp: string;
  message: string;
}

export interface RouterStatus {
  router_id: string;
  cliente_id?: number;
  state: "on" | "off";
  ip: string;
  uptime: number;
  last_state_change: string;
  logs: RouterLogEntry[];
  conectado: boolean;
  modo: string;
  latencia_ms: number;
  actualizado_en: string;
}

export interface ClienteCreatePayload {
  nombre: string;
  rfc: string;
  email: string;
  telefono: string;
  plan_id: string;
  domicilio: {
    calle: string;
    numero: string;
    colonia: string;
    cp: string;
    ciudad: string;
    estado: string;
    zona: string;
  };
  contacto: {
    nombre: string;
    email: string;
    telefono: string;
  };
  consentimiento: {
    marketing: boolean;
    terminos: boolean;
  };
}

export type RouterPowerAction = "on" | "off" | "reboot";

const clients: Record<string, AxiosInstance> = {};

function getClient(baseKey: Parameters<typeof getServiceUrl>[0], timeout = 7000) {
  const key = `${baseKey}-${timeout}`;
  if (!clients[key]) {
    clients[key] = axios.create({
      baseURL: getServiceUrl(baseKey),
      timeout
    });
  }
  return clients[key];
}

const demoState = {
  cliente: {
    id: 1,
    nombre: "María Hernández",
    rfc: "HEMM800101XX1",
    email: "maria@example.com",
    telefono: "+525512345678",
    estatus: "activo",
    zona: "NORTE",
    plan_id: "INT100"
  } satisfies ClientSummary,
  facturas: [
    { uuid: "CFDI-DEMO-001", total: 299.0, estatus: "timbrado" },
    { uuid: "CFDI-DEMO-000", total: 299.0, estatus: "pendiente" }
  ] satisfies FacturaSummary[],
  pagos: [
    {
      referencia: "PAGO-DEMO-001",
      metodo: "spei",
      monto: 299.0,
      estatus: "confirmado",
      creadoEn: new Date().toISOString()
    }
  ] satisfies PagoSummary[],
  tickets: [] as TicketSummary[],
  instalaciones: [
    {
      id: 101,
      clienteId: 1,
      estado: "Completada",
      ventana: "9-12",
      zona: "NORTE",
      notas: "Instalación demo",
      evidencias: ["https://placehold.co/200x120"],
      creadoEn: new Date().toISOString()
    }
  ] satisfies InstalacionSummary[],
  router: {
    router_id: "router-demo",
    cliente_id: 1,
    state: "on",
    ip: "10.10.1.10",
    uptime: 1200,
    last_state_change: new Date().toISOString(),
    logs: [
      { timestamp: new Date().toISOString(), message: "Router inicializado" },
      { timestamp: new Date().toISOString(), message: "Conexión establecida" }
    ],
    conectado: true,
    modo: "simulado",
    latencia_ms: 25,
    actualizado_en: new Date().toISOString()
  } satisfies RouterStatus
};

export function mapRouterStatus(clienteId: number, raw: any): RouterStatus {
  const logs = Array.isArray(raw?.logs)
    ? raw.logs.map((log: any) => ({
        timestamp: log?.timestamp ?? new Date().toISOString(),
        message: log?.message ?? String(log ?? "")
      }))
    : [];
  const state = raw?.state === "off" ? "off" : "on";
  const lastStateChange = raw?.last_state_change ?? raw?.timestamp ?? new Date().toISOString();
  const latency = typeof raw?.latencia_ms === "number" ? raw.latencia_ms : Math.max(8, Math.round((raw?.uptime ?? 0) % 40) + 12);
  return {
    router_id: raw?.router_id ?? raw?.id ?? `router-${clienteId}`,
    cliente_id: raw?.cliente_id ?? clienteId,
    state,
    ip: raw?.ip ?? raw?.ip_fake ?? "10.10.0.10",
    uptime: typeof raw?.uptime === "number" ? raw.uptime : 0,
    last_state_change: lastStateChange,
    logs,
    conectado: state === "on",
    modo: raw?.modo ?? "simulado",
    latencia_ms: latency,
    actualizado_en: lastStateChange
  };
}

async function withDemo<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    console.warn("[portal-cliente] API fallback → demo mode", error);
    return fallback;
  }
}

export async function fetchCliente(clienteId: number): Promise<ClientSummary> {
  return withDemo(
    async () => {
      const http = getClient("VITE_API_CLIENTES_URL");
      const { data } = await http.get<ClientSummary>(`/clientes/${clienteId}`);
      return data;
    },
    { ...demoState.cliente, id: clienteId }
  );
}

export async function fetchFacturas(clienteId: number): Promise<FacturaSummary[]> {
  return withDemo(async () => {
    const http = getClient("VITE_API_FACTURACION_URL");
    const { data } = await http.get<FacturaSummary[]>(`/facturacion/cliente/${clienteId}`);
    return data;
  }, demoState.facturas);
}

export async function fetchPagos(clienteId: number): Promise<PagoSummary[]> {
  return withDemo(async () => {
    const http = getClient("VITE_API_PAGOS_URL");
    const { data } = await http.get<PagoSummary[]>(`/pagos/cliente/${clienteId}`);
    return data;
  }, demoState.pagos);
}

export async function fetchTickets(clienteId: number): Promise<TicketSummary[]> {
  return withDemo(async () => {
    const http = getClient("VITE_API_TICKETS_URL");
    const { data } = await http.get<TicketSummary[]>(`/tickets/cliente/${clienteId}`);
    return data;
  }, demoState.tickets);
}

export async function fetchInstalaciones(clienteId: number): Promise<InstalacionSummary[]> {
  return withDemo(async () => {
    const http = getClient("VITE_API_INSTALACIONES_URL");
    const { data } = await http.get<InstalacionSummary[]>(`/instalaciones/cliente/${clienteId}`);
    return data;
  }, demoState.instalaciones);
}

export async function fetchRouterStatus(clienteId: number): Promise<RouterStatus> {
  return withDemo(async () => {
    const http = getClient("VITE_API_CLIENTES_URL");
    const { data } = await http.get(`/clientes/${clienteId}/router`);
    return mapRouterStatus(clienteId, data);
  }, { ...demoState.router, cliente_id: clienteId });
}

export async function registrarCliente(payload: ClienteCreatePayload): Promise<ClientSummary> {
  return withDemo(
    async () => {
      const http = getClient("VITE_API_CLIENTES_URL");
      const { data } = await http.post<ClientSummary>("/clientes", payload);
      return data;
    },
    {
      ...demoState.cliente,
      id: Math.floor(Math.random() * 1000) + 100,
      nombre: payload.nombre,
      rfc: payload.rfc,
      email: payload.email,
      telefono: payload.telefono,
      plan_id: payload.plan_id,
      router_id: demoState.router.router_id
    }
  );
}

export async function controlarRouter(clienteId: number, action: RouterPowerAction): Promise<RouterStatus> {
  return withDemo(
    async () => {
      const http = getClient("VITE_API_CLIENTES_URL");
      const { data } = await http.post(`/clientes/${clienteId}/router/power`, { action });
      return mapRouterStatus(clienteId, data);
    },
    mapRouterStatus(clienteId, {
      ...demoState.router,
      cliente_id: clienteId,
      state: action === "off" ? "off" : "on",
      last_state_change: new Date().toISOString()
    })
  );
}

export async function registrarPago(payload: {
  cliente_id: number;
  monto: number;
  metodo: string;
  to?: string;
}): Promise<void> {
  await withDemo(async () => {
    const http = getClient("VITE_API_ORQUESTADOR_URL", 15000);
    await http.post("/saga/procesar-pago", {
      ...payload,
      idem: crypto.randomUUID()
    });
  }, undefined);
}

export async function crearTicket(payload: {
  tipo: string;
  prioridad: string;
  descripcion: string;
  zona: string;
  clienteId: number;
}): Promise<TicketSummary> {
  return withDemo(async () => {
    const http = getClient("VITE_API_TICKETS_URL");
    const { data } = await http.post<TicketSummary>("/tickets", {
      tipo: payload.tipo,
      prioridad: payload.prioridad,
      zona: payload.zona,
      clienteId: payload.clienteId,
      notas: payload.descripcion
    });
    return data;
  }, {
    id: Math.floor(Math.random() * 1000) + 200,
    tipo: payload.tipo,
    prioridad: payload.prioridad,
    estado: "Abierto",
    zona: payload.zona,
    clienteId: payload.clienteId,
    asignadoA: "zona-demo-01",
    slaAt: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    creadoEn: new Date().toISOString()
  });
}

export async function solicitarCorte(clienteId: number): Promise<void> {
  await withDemo(async () => {
    const http = getClient("VITE_API_RED_URL");
    await http.post("/router/cortar", { cliente_id: clienteId });
  }, undefined);
}

export async function solicitarReconectar(clienteId: number): Promise<void> {
  await withDemo(async () => {
    const http = getClient("VITE_API_RED_URL");
    await http.post("/router/reconectar", { cliente_id: clienteId });
  }, undefined);
}
