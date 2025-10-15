import { useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  crearTicket,
  controlarRouter,
  fetchCliente,
  fetchFacturas,
  fetchInstalaciones,
  fetchPagos,
  fetchRouterStatus,
  fetchTickets,
  mapRouterStatus,
  registrarCliente,
  registrarPago,
  solicitarCorte,
  solicitarReconectar
} from "./api/http";
import type { ClienteCreatePayload, RouterPowerAction } from "./api/http";
import { useClienteSession } from "./hooks/useClienteSession";
import { PortalDataContext, type PortalData } from "./context/PortalDataContext";
import DashboardPage from "./pages/DashboardPage";
import PaymentsPage from "./pages/PaymentsPage";
import TicketsPage from "./pages/TicketsPage";
import ProfilePage from "./pages/ProfilePage";
import MiRouterPage from "./pages/MiRouterPage";
import { getServiceUrl } from "./config";

const navItems = [
  { to: "/cliente", label: "Mi Router" },
  { to: "/resumen", label: "Resumen" },
  { to: "/pagos", label: "Pagos" },
  { to: "/tickets", label: "Tickets" },
  { to: "/perfil", label: "Perfil" }
];

export default function App() {
  const { clienteId, update: updateSession, clear } = useClienteSession();
  const [inputId, setInputId] = useState(() => (clienteId ? String(clienteId) : ""));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PortalData>({
    cliente: null,
    facturas: [],
    pagos: [],
    tickets: [],
    instalaciones: [],
    router: null,
    zona: null
  });
  const [routerStreamMode, setRouterStreamMode] = useState<"idle" | "ws" | "polling">("idle");

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!clienteId) {
      setData((prev) => ({ ...prev, cliente: null }));
      setRouterStreamMode("idle");
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [cliente, facturas, pagos, tickets, instalaciones, router] = await Promise.all([
          fetchCliente(clienteId),
          fetchFacturas(clienteId),
          fetchPagos(clienteId),
          fetchTickets(clienteId),
          fetchInstalaciones(clienteId),
          fetchRouterStatus(clienteId)
        ]);
        if (cancelled) return;
        setData({
          cliente,
          facturas,
          pagos,
          tickets,
          instalaciones,
          router,
          zona: cliente?.zona ?? null
        });
        if (location.pathname === "/") {
          navigate("/", { replace: true });
        }
      } catch (err: unknown) {
        console.error(err);
        if (!cancelled) {
          setError("No se pudo cargar la información del cliente. Activa modo demo o revisa los servicios.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [clienteId, location.pathname, navigate]);

  const isAuthenticated = Boolean(clienteId && data.cliente);

  const portalValue = useMemo(() => data, [data]);

  async function handleLookup(id: number) {
    if (!id || Number.isNaN(id)) {
      setError("Ingresa un número de cliente válido.");
      return;
    }
    updateSession(id);
  }

  const handlePago = async (payload: Parameters<typeof registrarPago>[0]) => {
    await registrarPago(payload);
    if (clienteId) {
      const [pagos, router] = await Promise.all([fetchPagos(clienteId), fetchRouterStatus(clienteId)]);
      setData((prev) => ({ ...prev, pagos, router }));
    }
  };

  const handleNuevoTicket = async (payload: Parameters<typeof crearTicket>[0]) => {
    const ticket = await crearTicket(payload);
    setData((prev) => ({ ...prev, tickets: [ticket, ...prev.tickets] }));
  };

  const handleCorte = async () => {
    if (!clienteId) return;
    await solicitarCorte(clienteId);
    const router = await fetchRouterStatus(clienteId);
    setData((prev) => ({ ...prev, router }));
  };

  const handleReconectar = async () => {
    if (!clienteId) return;
    await solicitarReconectar(clienteId);
    const router = await fetchRouterStatus(clienteId);
    setData((prev) => ({ ...prev, router }));
  };

  const handleRegistrarCliente = async (payload: ClienteCreatePayload) => {
    setError(null);
    setLoading(true);
    try {
      const nuevo = await registrarCliente(payload);
      updateSession(nuevo.id);
      setData((prev) => ({
        ...prev,
        cliente: nuevo,
        zona: nuevo.zona ?? null,
      }));
      if (nuevo.router_id) {
        try {
          const router = await fetchRouterStatus(nuevo.id);
          setData((prev) => ({ ...prev, router }));
        } catch (routerErr) {
          console.warn("No se pudo cargar el router recién creado", routerErr);
        }
      }
      return nuevo;
    } catch (err) {
      console.error(err);
      setError("No se pudo registrar el cliente. Intenta más tarde.");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleRouterPower = async (action: RouterPowerAction) => {
    if (!clienteId) return;
    try {
      const router = await controlarRouter(clienteId, action);
      setData((prev) => ({ ...prev, router }));
    } catch (err) {
      console.error(err);
      setError("No se pudo cambiar el estado del router. Verifica la conexión.");
      throw err;
    }
  };

  useEffect(() => {
    if (!clienteId || !data.cliente?.router_id) {
      setRouterStreamMode("idle");
      return;
    }

    let cancelled = false;
    let ws: WebSocket | null = null;
    let pollTimer: number | null = null;

    const fetchState = async () => {
      try {
        const router = await fetchRouterStatus(clienteId);
        if (!cancelled) {
          setData((prev) => ({ ...prev, router }));
        }
      } catch (err) {
        if (!cancelled) {
          console.warn("Fallo al obtener estado del router", err);
        }
      }
    };

    const startPolling = () => {
      if (pollTimer !== null) return;
      setRouterStreamMode("polling");
      pollTimer = window.setInterval(fetchState, 2000);
    };

    const stopPolling = () => {
      if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const connect = () => {
      const base = getServiceUrl("VITE_ROUTER_SIM_URL");
      const routerId = data.cliente?.router_id;
      if (!base || !routerId) {
        startPolling();
        return;
      }
      const wsUrl = base.replace(/^http/i, "ws") + `/ws/routers/${routerId}`;
      try {
        ws = new WebSocket(wsUrl);
      } catch (err) {
        console.warn("No fue posible abrir WebSocket", err);
        startPolling();
        return;
      }
      ws.onopen = () => {
        if (cancelled) return;
        stopPolling();
        setRouterStreamMode("ws");
      };
      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const payload = JSON.parse(event.data);
          const router = mapRouterStatus(clienteId, payload);
          setData((prev) => ({ ...prev, router }));
        } catch (err) {
          console.error("Error procesando evento de router", err);
        }
      };
      ws.onerror = () => {
        if (!cancelled) {
          startPolling();
          ws?.close();
        }
      };
      ws.onclose = () => {
        if (!cancelled) {
          ws = null;
          startPolling();
        }
      };
    };

    fetchState();
    connect();

    return () => {
      cancelled = true;
      if (ws) {
        ws.close();
      }
      stopPolling();
    };
  }, [clienteId, data.cliente?.router_id]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-30 bg-slate-950/80 backdrop-blur border-b border-slate-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase text-slate-400">Telecable MVP</p>
            <h1 className="text-lg font-semibold text-primary">Portal Cliente</h1>
          </div>
          <form
            className="flex items-center gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              handleLookup(Number(inputId));
            }}
          >
            <label className="text-xs text-slate-400 uppercase tracking-widest">
              Cliente
              <input
                className="ml-2 w-28 rounded border border-slate-700 bg-slate-900 px-3 py-1 text-sm outline-none focus:border-primary"
                value={inputId}
                onChange={(event) => setInputId(event.target.value)}
                placeholder="ID"
              />
            </label>
            <button
              type="submit"
              className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-primary-dark"
            >
              Consultar
            </button>
            {isAuthenticated && (
              <button
                type="button"
                className="text-xs text-slate-400 underline decoration-dotted"
                onClick={() => {
                  clear();
                  setInputId("");
                  setData({
                    cliente: null,
                    facturas: [],
                    pagos: [],
                    tickets: [],
                    instalaciones: [],
                    router: null,
                    zona: null
                  });
                }}
              >
                Cerrar demo
              </button>
            )}
          </form>
        </div>
        <nav className="border-t border-slate-800 bg-slate-900/60">
          <div className="mx-auto flex max-w-6xl gap-2 px-6 py-3 text-sm font-medium">
            {navItems.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  [
                    "rounded-full px-4 py-2 transition",
                    isActive ? "bg-primary text-slate-950" : "text-slate-400 hover:text-slate-100"
                  ].join(" ")
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-6">
        {error && (
          <div className="rounded border border-red-500/60 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}
        {!isAuthenticated && !loading && (
          <div className="glass rounded-3xl border border-slate-800 px-6 py-10 text-center shadow-2xl">
            <h2 className="text-2xl font-semibold text-slate-100">Bienvenido</h2>
            <p className="mt-3 text-sm text-slate-400">
              Ingresa tu número de cliente o utiliza el demo con ID <code>1</code>.
            </p>
          </div>
        )}
        <PortalDataContext.Provider value={portalValue}>
          <Routes>
            <Route
              path="/cliente"
              element={
                <MiRouterPage
                  loading={loading}
                  cliente={data.cliente}
                  router={data.router}
                  onRegister={handleRegistrarCliente}
                  onPower={handleRouterPower}
                  streamMode={routerStreamMode}
                  globalError={error}
                />
              }
            />
            <Route path="/" element={<Navigate to="/cliente" replace />} />
            <Route
              path="/resumen"
              element={
                <DashboardPage
                  loading={loading}
                  onRefresh={async () => {
                    if (clienteId) {
                      setError(null);
                      try {
                        setLoading(true);
                        const [facturas, pagos, tickets, instalaciones, router] = await Promise.all([
                          fetchFacturas(clienteId),
                          fetchPagos(clienteId),
                          fetchTickets(clienteId),
                          fetchInstalaciones(clienteId),
                          fetchRouterStatus(clienteId)
                        ]);
                        setData((prev) => ({
                          ...prev,
                          facturas,
                          pagos,
                          tickets,
                          instalaciones,
                          router
                        }));
                      } catch (err) {
                        console.error(err);
                        setError("No fue posible refrescar el estado. Revisa los servicios.");
                      } finally {
                        setLoading(false);
                      }
                    }
                  }}
                  onCorte={handleCorte}
                  onReconectar={handleReconectar}
                />
              }
            />
            <Route
              path="/pagos"
              element={
                <PaymentsPage
                  loading={loading}
                  onRegistrarPago={async (payload) => {
                    if (!clienteId) return;
                    await handlePago({ ...payload, cliente_id: clienteId });
                  }}
                />
              }
            />
            <Route
              path="/tickets"
              element={
                <TicketsPage
                  loading={loading}
                  onCreate={async (ticket) => {
                    if (!clienteId || !data.cliente) return;
                    await handleNuevoTicket({
                      ...ticket,
                      clienteId,
                      zona: data.cliente.zona ?? "NORTE"
                    });
                  }}
                />
              }
            />
            <Route path="/perfil" element={<ProfilePage loading={loading} />} />
          </Routes>
        </PortalDataContext.Provider>
      </main>

      <footer className="mt-12 border-t border-slate-800 bg-slate-950/80 px-6 py-6 text-center text-xs text-slate-500">
        <p>
          Telecable MVP · Demo interactiva · Datos en vivo cuando la infraestructura está activa, con modo demo como
          respaldo.
        </p>
      </footer>
    </div>
  );
}
