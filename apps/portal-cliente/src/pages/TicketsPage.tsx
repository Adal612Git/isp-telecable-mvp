import { FormEvent, useState } from "react";
import { usePortalData } from "../context/PortalDataContext";
import { formatDateTime } from "../utils/format";

interface Props {
  loading: boolean;
  onCreate: (input: { tipo: string; prioridad: string; descripcion: string }) => Promise<void>;
}

export default function TicketsPage({ loading, onCreate }: Props) {
  const { tickets, cliente } = usePortalData();
  const [tipo, setTipo] = useState("internet");
  const [prioridad, setPrioridad] = useState("P3");
  const [descripcion, setDescripcion] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cliente) {
      setStatus("Selecciona primero un cliente.");
      return;
    }
    setStatus("Enviando ticket...");
    try {
      await onCreate({ tipo, prioridad, descripcion });
      setDescripcion("");
      setStatus("Ticket creado correctamente ✅");
    } catch (err) {
      console.error(err);
      setStatus("No fue posible crear el ticket. Revisa la consola o los servicios.");
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="glass card-border rounded-3xl p-6">
        <h2 className="text-lg font-semibold text-slate-100">Levantar ticket</h2>
        <form className="mt-4 space-y-4 text-sm" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-xs uppercase text-slate-400">Tipo</span>
            <select
              value={tipo}
              onChange={(event) => setTipo(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-primary"
            >
              <option value="internet">Internet</option>
              <option value="facturacion">Facturación</option>
              <option value="wifi">Cobertura WiFi</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase text-slate-400">Prioridad</span>
            <select
              value={prioridad}
              onChange={(event) => setPrioridad(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-primary"
            >
              <option value="P1">Crítica</option>
              <option value="P2">Alta</option>
              <option value="P3">Normal</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase text-slate-400">Descripción</span>
            <textarea
              rows={3}
              value={descripcion}
              onChange={(event) => setDescripcion(event.target.value)}
              placeholder="Describe brevemente el problema…"
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-primary"
            />
          </label>
          <button
            disabled={loading}
            className="w-full rounded-full bg-primary px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-primary-dark disabled:opacity-60"
          >
            {loading ? "Enviando..." : "Enviar ticket"}
          </button>
        </form>
        {status && <p className="mt-3 text-xs text-slate-400">{status}</p>}
      </section>

      <section className="glass card-border rounded-3xl p-6">
        <h2 className="text-lg font-semibold text-slate-100">Historial</h2>
        <ul className="mt-4 space-y-3 text-sm">
          {tickets.map((ticket) => (
            <li key={ticket.id} className="rounded border border-slate-800/70 px-3 py-3">
              <div className="flex items-center justify-between text-xs uppercase text-slate-400">
                <span>#{ticket.id}</span>
                <span>{ticket.estado}</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
                <span>Prioridad {ticket.prioridad}</span>
                <span>SLA {formatDateTime(ticket.slaAt)}</span>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Asignado a {ticket.asignadoA} · Zona {ticket.zona}
              </div>
            </li>
          ))}
          {!tickets.length && <li className="text-xs text-slate-500">Aún no hay tickets. Crea uno con el formulario.</li>}
        </ul>
      </section>
    </div>
  );
}
