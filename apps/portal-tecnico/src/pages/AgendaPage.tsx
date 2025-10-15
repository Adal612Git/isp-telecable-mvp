import { FormEvent, useState } from "react";
import { useTechnician } from "../context";
import { formatDate } from "../utils";

interface Props {
  loading: boolean;
  onChangeEstado: (
    id: number,
    estado: "EnRuta" | "Completada",
    extras?: { evidencias?: string; notas?: string }
  ) => Promise<void>;
}

export default function AgendaPage({ loading, onChangeEstado }: Props) {
  const { agenda } = useTechnician();
  const [formId, setFormId] = useState<number | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>, estado: "EnRuta" | "Completada") {
    event.preventDefault();
    if (formId === null) return;
    const formData = new FormData(event.currentTarget);
    const evidencias = String(formData.get("evidencias") ?? "");
    const notas = String(formData.get("notas") ?? "");
    void onChangeEstado(formId, estado, { evidencias, notas });
    if (estado === "Completada") {
      setFormId(null);
      event.currentTarget.reset();
    }
  }

  return (
    <section className="grid gap-6 md:grid-cols-2">
      <article className="card md:col-span-2">
        <h2 className="text-lg font-semibold">Instalaciones asignadas</h2>
        <div className="mt-4 overflow-x-auto text-sm">
          <table className="min-w-full text-left">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Folio</th>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2">Ventana</th>
                <th className="px-3 py-2">Estado</th>
                <th className="px-3 py-2">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {agenda.map((inst) => (
                <tr key={inst.id} className="border-t border-slate-800/70">
                  <td className="px-3 py-2 text-xs">#{inst.id}</td>
                  <td className="px-3 py-2 text-xs">{inst.clienteId}</td>
                  <td className="px-3 py-2 text-xs">{inst.ventana}</td>
                  <td className="px-3 py-2 text-xs">{inst.estado}</td>
                  <td className="px-3 py-2 text-xs">
                    <div className="flex gap-2">
                      <button
                        disabled={loading}
                        onClick={() => void onChangeEstado(inst.id, "EnRuta")}
                        className="rounded-full border border-primary/60 px-3 py-1 text-xs text-primary hover:bg-primary/10"
                      >
                        En ruta
                      </button>
                      <button
                        disabled={loading}
                        onClick={() => setFormId(inst.id)}
                        className="rounded-full border border-emerald-400/60 px-3 py-1 text-xs text-emerald-300 hover:bg-emerald-400/10"
                      >
                        Completar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!agenda.length && (
                <tr>
                  <td className="px-3 py-6 text-center text-xs text-slate-500" colSpan={5}>
                    Sin instalaciones en la agenda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>

      {formId !== null && (
        <article className="card">
          <h3 className="text-sm font-semibold uppercase text-slate-400">Cerrar instalación #{formId}</h3>
          <form className="mt-4 space-y-3 text-sm" onSubmit={(event) => handleSubmit(event, "Completada")}>
            <label className="block">
              <span className="text-xs uppercase text-slate-500">Evidencias (URLs)</span>
              <input
                name="evidencias"
                placeholder="https://foto1.png, https://foto2.png"
                className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 focus:border-primary"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase text-slate-500">Notas</span>
              <textarea
                name="notas"
                rows={3}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 focus:border-primary"
              />
            </label>
            <button
              disabled={loading}
              className="w-full rounded-full bg-emerald-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-300 disabled:opacity-60"
            >
              Confirmar cierre
            </button>
          </form>
        </article>
      )}

      <article className="card">
        <h3 className="text-sm font-semibold uppercase text-slate-400">Resumen rápido</h3>
        <ul className="mt-3 space-y-2 text-xs text-slate-400">
          {agenda.map((inst) => (
            <li key={inst.id}>
              #{inst.id} · {inst.estado} · {formatDate(inst.creadoEn)}
            </li>
          ))}
          {!agenda.length && <li>No hay visitas registradas.</li>}
        </ul>
      </article>
    </section>
  );
}
