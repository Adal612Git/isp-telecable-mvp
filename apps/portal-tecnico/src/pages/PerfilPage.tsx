import { useTechnician } from "../context";
import { formatDate } from "../utils";

interface Props {
  loading: boolean;
  onReload: () => Promise<void>;
}

export default function PerfilPage({ loading, onReload }: Props) {
  const { tecnico, zona, agenda, tickets } = useTechnician();
  const completadas = agenda.filter((item) => item.estado === "Completada").length;
  const abiertos = tickets.filter((ticket) => ticket.estado !== "Resuelto").length;

  return (
    <section className="card">
      <h2 className="text-lg font-semibold">Perfil del técnico</h2>
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        <article>
          <h3 className="text-sm font-semibold uppercase text-slate-400">Datos</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li>Nombre: {tecnico ?? "Sin sesión"}</li>
            <li>Zona: {zona ?? "N/A"}</li>
            <li>Instalaciones completadas: {completadas}</li>
            <li>Tickets abiertos: {abiertos}</li>
          </ul>
          <button
            className="mt-4 rounded-full border border-slate-600 px-4 py-2 text-xs text-slate-300 hover:border-primary disabled:opacity-60"
            disabled={loading}
            onClick={() => void onReload()}
          >
            Refrescar métricas
          </button>
        </article>
        <article>
          <h3 className="text-sm font-semibold uppercase text-slate-400">Agenda</h3>
          <ul className="mt-3 space-y-2 text-xs text-slate-400">
            {agenda.map((inst) => (
              <li key={inst.id}>
                #{inst.id} · {inst.estado} · {formatDate(inst.creadoEn)}
              </li>
            ))}
            {!agenda.length && <li>No hay instalaciones registradas.</li>}
          </ul>
        </article>
      </div>
    </section>
  );
}
