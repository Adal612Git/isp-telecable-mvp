import { useTechnician } from "../context";
import { formatDate } from "../utils";

interface Props {
  loading: boolean;
  onResolver: (id: number) => Promise<void>;
}

export default function TicketsPage({ loading, onResolver }: Props) {
  const { tickets } = useTechnician();
  return (
    <section className="card">
      <h2 className="text-lg font-semibold">Tickets en zona</h2>
      <p className="mt-2 text-sm text-slate-400">
        Marca como resuelto para actualizar el SLA en el servicio de tickets.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2">Prioridad</th>
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2">SLA</th>
              <th className="px-3 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket) => (
              <tr key={ticket.id} className="border-t border-slate-800/70 text-xs">
                <td className="px-3 py-2">#{ticket.id}</td>
                <td className="px-3 py-2 capitalize">{ticket.tipo}</td>
                <td className="px-3 py-2">{ticket.prioridad}</td>
                <td className="px-3 py-2">{ticket.estado}</td>
                <td className="px-3 py-2">{formatDate(ticket.slaAt)}</td>
                <td className="px-3 py-2">
                  {ticket.estado !== "Resuelto" ? (
                    <button
                      disabled={loading}
                      onClick={() => void onResolver(ticket.id)}
                      className="rounded-full border border-emerald-400/60 px-3 py-1 text-emerald-300 hover:bg-emerald-400/10"
                    >
                      Marcar resuelto
                    </button>
                  ) : (
                    <span className="text-emerald-300">Completado</span>
                  )}
                </td>
              </tr>
            ))}
            {!tickets.length && (
              <tr>
                <td className="px-3 py-6 text-center text-xs text-slate-500" colSpan={6}>
                  No hay tickets asignados en esta zona.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
