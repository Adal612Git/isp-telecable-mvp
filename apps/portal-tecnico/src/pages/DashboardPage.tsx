import { useTechnician } from "../context";

interface Props {
  loading: boolean;
}

export default function DashboardPage({ loading }: Props) {
  const { agenda, tickets, zona, tecnico, ping } = useTechnician();
  const completadas = agenda.filter((item) => item.estado === "Completada").length;
  const pendientes = agenda.length - completadas;
  const ticketsAbiertos = tickets.filter((ticket) => ticket.estado !== "Resuelto").length;

  return (
    <section className="grid gap-6 md:grid-cols-3">
      <article className="card">
        <p className="text-xs uppercase text-slate-500">Cuadrilla</p>
        <h2 className="mt-2 text-lg font-semibold">{tecnico ?? "Sin sesión"}</h2>
        <p className="mt-1 text-sm text-slate-400">Zona {zona ?? "N/A"}</p>
        {loading && <p className="mt-4 text-xs text-slate-500">Cargando datos…</p>}
      </article>
      <article className="card">
        <p className="text-xs uppercase text-slate-500">Instalaciones</p>
        <h2 className="mt-2 text-lg font-semibold">{agenda.length}</h2>
        <p className="text-sm text-emerald-300">{completadas} completadas</p>
        <p className="text-sm text-slate-400">{pendientes} pendientes</p>
      </article>
      <article className="card">
        <p className="text-xs uppercase text-slate-500">Tickets</p>
        <h2 className="mt-2 text-lg font-semibold">{tickets.length}</h2>
        <p className="text-sm text-amber-300">{ticketsAbiertos} abiertos</p>
        {ping && (
          <p className="mt-3 text-xs text-slate-400">
            Último ping: {ping.latency_ms} ms {ping.estado?.conectado ? "(OK)" : "(Alerta)"}
          </p>
        )}
      </article>
    </section>
  );
}
