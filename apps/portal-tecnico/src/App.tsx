import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  fetchAgenda,
  fetchInventario,
  fetchTickets,
  fetchRouters,
  controlRouter,
  type RouterSummary,
  type RouterPowerAction,
  marcarTicketResuelto,
  pingHost,
  traceroute,
  updateInstalacionEstado,
  type InstalacionRow,
  type RouterPing,
  type TicketRow
} from "./api";
import { TechnicianContext } from "./context";
import { useTechnicianSession } from "./useTechnicianSession";
import DashboardPage from "./pages/DashboardPage";
import AgendaPage from "./pages/AgendaPage";
import DiagnosticoPage from "./pages/DiagnosticoPage";
import TicketsPage from "./pages/TicketsPage";
import PerfilPage from "./pages/PerfilPage";
import InventarioPage from "./pages/InventarioPage";
import RoutersPage from "./pages/RoutersPage";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/routers", label: "Routers" },
  { to: "/agenda", label: "Agenda" },
  { to: "/diagnostico", label: "Diagnóstico" },
  { to: "/tickets", label: "Tickets" },
  { to: "/inventario", label: "Inventario" },
  { to: "/perfil", label: "Perfil" }
];

export default function App() {
  const { zona, nombre, setSession, clearSession } = useTechnicianSession();
  const [agenda, setAgenda] = useState<InstalacionRow[]>([]);
  const [tickets, setTickets] = useState<TicketRow[]>([]);
  const [inventario, setInventario] = useState<unknown>(null);
  const [ping, setPing] = useState<RouterPing | null>(null);
  const [routers, setRouters] = useState<RouterSummary[]>([]);
  const [routerLoading, setRouterLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const authenticated = Boolean(zona && nombre);

  useEffect(() => {
    if (!zona) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [agendaData, ticketData, inventarioData] = await Promise.all([
          fetchAgenda(zona),
          fetchTickets(zona),
          fetchInventario(zona)
        ]);
        if (cancelled) return;
        setAgenda(agendaData);
        setTickets(ticketData);
        setInventario(inventarioData);
      } catch (error) {
        console.error(error);
        if (!cancelled) setStatus("No se pudo cargar la información de la zona. Activa modo demo o revisa la API.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [zona]);

  useEffect(() => {
    if (!authenticated) {
      setRouters([]);
      return;
    }
    void loadRouters(true);
    const interval = window.setInterval(() => {
      void loadRouters(true);
    }, 5000);
    return () => {
      window.clearInterval(interval);
    };
  }, [authenticated, loadRouters]);

  const contextValue = useMemo(
    () => ({
      zona,
      tecnico: nombre,
      agenda,
      tickets,
      inventario,
      ping,
      routers
    }),
    [zona, nombre, agenda, tickets, inventario, ping, routers]
  );

  const loadRouters = useCallback(
    async (silent = false) => {
      if (!authenticated) {
        setRouters([]);
        return;
      }
      if (!silent) setRouterLoading(true);
      try {
        const list = await fetchRouters();
        setRouters(list);
      } catch (error) {
        console.error(error);
        if (!silent) {
          setStatus("No se pudo actualizar el listado de routers.");
        }
      } finally {
        if (!silent) setRouterLoading(false);
      }
    },
    [authenticated]
  );

  const handleLogin = (data: { zona: string; nombre: string }) => {
    setSession(data.zona, data.nombre);
    setStatus(null);
    navigate("/");
  };

  const handleInstalacionUpdate = async (
    id: number,
    estado: "EnRuta" | "Completada",
    extras?: { evidencias?: string; notas?: string }
  ) => {
    if (!zona) return;
    setLoading(true);
    try {
      const evidencias = extras?.evidencias
        ?.split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      await updateInstalacionEstado(id, estado, evidencias, extras?.notas);
      const agendaData = await fetchAgenda(zona);
      setAgenda(agendaData);
      setStatus(`Instalación #${id} → ${estado}`);
    } catch (error) {
      console.error(error);
      setStatus("No fue posible actualizar la instalación.");
    } finally {
      setLoading(false);
    }
  };

  const handlePing = async (host: string, clienteId?: number) => {
    try {
      const result = await pingHost(host, clienteId);
      setPing(result);
      setStatus(`Ping ${host}: ${result.latency_ms} ms`);
    } catch (error) {
      console.error(error);
      setStatus("Ping no disponible en este momento.");
    }
  };

  const handleTraceroute = async (host: string) => {
    try {
      const result = await traceroute(host);
      setStatus(`Traceroute ${host}: ${result.hops.join(" → ")}`);
      return result.hops;
    } catch (error) {
      console.error(error);
      setStatus("Traceroute no disponible.");
      return [];
    }
  };

  const handleRouterAction = async (routerId: string, action: RouterPowerAction) => {
    try {
      setRouterLoading(true);
      await controlRouter(routerId, action);
      await loadRouters(true);
      setStatus(`Router ${routerId} → ${action}`);
    } catch (error) {
      console.error(error);
      setStatus("No se pudo ejecutar la acción del router.");
    } finally {
      setRouterLoading(false);
    }
  };

  const handleRoutersRefresh = async () => {
    await loadRouters(false);
  };

  const handleTicketResuelto = async (id: number) => {
    if (!zona) return;
    try {
      await marcarTicketResuelto(id);
      const ticketData = await fetchTickets(zona);
      setTickets(ticketData);
      setStatus(`Ticket #${id} marcado como resuelto.`);
    } catch (error) {
      console.error(error);
      setStatus("No fue posible actualizar el ticket.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase text-slate-500">Telecable MVP</p>
            <h1 className="text-lg font-semibold text-primary">Panel Técnico</h1>
          </div>
          <form
            className="flex flex-col gap-2 text-xs md:flex-row md:items-end md:gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              const formData = new FormData(event.currentTarget);
              const name = String(formData.get("nombre") ?? "").trim();
              const zone = String(formData.get("zona") ?? "").trim();
              if (!name || !zone) {
                setStatus("Completa nombre y zona para iniciar la demo.");
                return;
              }
              handleLogin({ nombre: name, zona: zone });
            }}
          >
            <label className="flex flex-col text-slate-400">
              Nombre
              <input
                name="nombre"
                defaultValue={nombre ?? ""}
                placeholder="Técnico"
                className="mt-1 rounded border border-slate-700 bg-slate-900 px-3 py-1 text-slate-100 focus:border-primary"
              />
            </label>
            <label className="flex flex-col text-slate-400">
              Zona
              <select
                name="zona"
                defaultValue={zona ?? "NORTE"}
                className="mt-1 rounded border border-slate-700 bg-slate-900 px-3 py-1 text-slate-100 focus:border-primary"
              >
                <option value="NORTE">NORTE</option>
                <option value="CENTRO">CENTRO</option>
                <option value="SUR">SUR</option>
              </select>
            </label>
            <button className="rounded-full bg-primary px-4 py-2 text-slate-950">Entrar</button>
            {authenticated && (
              <button
                type="button"
                className="text-slate-400 underline"
                onClick={() => {
                  clearSession();
                  setAgenda([]);
                  setTickets([]);
                  setInventario(null);
                  setPing(null);
                  setRouters([]);
                }}
              >
                Salir
              </button>
            )}
          </form>
        </div>
        <nav className="border-t border-slate-800/70">
          <div className="mx-auto flex max-w-6xl gap-2 px-6 py-3 text-sm">
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
        {status && (
          <div className="rounded border border-primary/30 bg-primary/10 px-4 py-3 text-xs text-primary">{status}</div>
        )}
        {!authenticated && (
          <div className="card text-center">
            <h2 className="text-xl font-semibold">Inicia la demo técnica</h2>
            <p className="mt-2 text-sm text-slate-400">
              Introduce un nombre y la zona que deseas operar para cargar la agenda y tickets asignados.
            </p>
          </div>
        )}
        <TechnicianContext.Provider value={contextValue}>
          <Routes>
            <Route path="/" element={<DashboardPage loading={loading} />} />
            <Route
              path="/routers"
              element={
                <RoutersPage
                  loading={routerLoading}
                  routers={routers}
                  onRefresh={handleRoutersRefresh}
                  onAction={handleRouterAction}
                />
              }
            />
            <Route
              path="/agenda"
              element={<AgendaPage loading={loading} onChangeEstado={handleInstalacionUpdate} />}
            />
            <Route
              path="/diagnostico"
              element={<DiagnosticoPage loading={loading} onPing={handlePing} onTraceroute={handleTraceroute} />}
            />
            <Route path="/tickets" element={<TicketsPage loading={loading} onResolver={handleTicketResuelto} />} />
            <Route path="/inventario" element={<InventarioPage loading={loading} />} />
            <Route
              path="/perfil"
              element={
                <PerfilPage
                  loading={loading}
                  onReload={async () => {
                    if (!zona) return;
                    const [agendaData, ticketData] = await Promise.all([fetchAgenda(zona), fetchTickets(zona)]);
                    setAgenda(agendaData);
                    setTickets(ticketData);
                  }}
                />
              }
            />
            <Route path="/tecnico" element={<DashboardPage loading={loading} />} />
            <Route
              path="/tecnico/routers"
              element={
                <RoutersPage
                  loading={routerLoading}
                  routers={routers}
                  onRefresh={handleRoutersRefresh}
                  onAction={handleRouterAction}
                />
              }
            />
            <Route
              path="/tecnico/agenda"
              element={<AgendaPage loading={loading} onChangeEstado={handleInstalacionUpdate} />}
            />
            <Route
              path="/tecnico/diagnostico"
              element={<DiagnosticoPage loading={loading} onPing={handlePing} onTraceroute={handleTraceroute} />}
            />
            <Route
              path="/tecnico/tickets"
              element={<TicketsPage loading={loading} onResolver={handleTicketResuelto} />}
            />
            <Route path="/tecnico/inventario" element={<InventarioPage loading={loading} />} />
            <Route
              path="/tecnico/perfil"
              element={
                <PerfilPage
                  loading={loading}
                  onReload={async () => {
                    if (!zona) return;
                    const [agendaData, ticketData] = await Promise.all([fetchAgenda(zona), fetchTickets(zona)]);
                    setAgenda(agendaData);
                    setTickets(ticketData);
                  }}
                />
              }
            />
          </Routes>
        </TechnicianContext.Provider>
      </main>

      <footer className="border-t border-slate-800/60 bg-slate-950/80 px-6 py-6 text-center text-xs text-slate-500">
        Telecable MVP · Operaciones técnicas en modo demo o conectado a microservicios reales.
      </footer>
    </div>
  );
}
