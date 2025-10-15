import { FormEvent, useState } from "react";
import { useTechnician } from "../context";
import { formatDate } from "../utils";

interface Props {
  loading: boolean;
  onPing: (host: string, clienteId?: number) => Promise<void>;
  onTraceroute: (host: string) => Promise<string[]>;
}

export default function DiagnosticoPage({ loading, onPing, onTraceroute }: Props) {
  const { ping, zona, agenda } = useTechnician();
  const [host, setHost] = useState("8.8.8.8");
  const [clienteId, setClienteId] = useState("");
  const [traceroute, setTraceroute] = useState<string[]>([]);

  function handlePing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = clienteId ? Number(clienteId) : undefined;
    void onPing(host, id);
  }

  async function handleTraceroute() {
    const hops = await onTraceroute(host);
    setTraceroute(hops);
  }

  return (
    <section className="grid gap-6 md:grid-cols-2">
      <article className="card">
        <h2 className="text-lg font-semibold">Diagnóstico interactivo</h2>
        <p className="mt-2 text-sm text-slate-400">
          Ejecuta ping y traceroute hacia hosts clave. El servicio de red responde en modo emulado.
        </p>
        <form className="mt-4 space-y-3 text-sm" onSubmit={handlePing}>
          <label className="block">
            <span className="text-xs uppercase text-slate-500">Host / IP</span>
            <input
              value={host}
              onChange={(event) => setHost(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 focus:border-primary"
            />
          </label>
          <label className="block">
            <span className="text-xs uppercase text-slate-500">Cliente (opcional)</span>
            <input
              value={clienteId}
              onChange={(event) => setClienteId(event.target.value)}
              placeholder="ID cliente"
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 focus:border-primary"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-primary/80 disabled:opacity-60"
            >
              Ejecutar ping
            </button>
            <button
              type="button"
              onClick={handleTraceroute}
              className="rounded-full border border-slate-600 px-4 py-2 text-xs text-slate-300 hover:border-primary"
            >
              Traceroute
            </button>
          </div>
        </form>
        {ping && (
          <div className="mt-4 rounded border border-slate-800/70 bg-slate-900/60 px-3 py-3 text-xs text-slate-300">
            <p>Host: {ping.host}</p>
            <p>Latencia: {ping.latency_ms} ms</p>
            {ping.estado && (
              <p>
                Cliente #{ping.estado.cliente_id} · {ping.estado.conectado ? "Conectado" : "Suspendido"} · IP{" "}
                {ping.estado.ip_fake ?? "0.0.0.0"}
              </p>
            )}
          </div>
        )}
      </article>

      <article className="card">
        <h3 className="text-sm font-semibold uppercase text-slate-400">Resultados</h3>
        {traceroute.length ? (
          <ol className="mt-3 space-y-1 text-xs text-slate-300">
            {traceroute.map((hop, index) => (
              <li key={`${hop}-${index}`}>{index + 1}. {hop}</li>
            ))}
          </ol>
        ) : (
          <p className="mt-3 text-xs text-slate-500">Sin traceroute ejecutado.</p>
        )}
        <div className="mt-6 text-xs text-slate-500">
          <p>
            Zona actual: <span className="text-slate-300">{zona ?? "N/A"}</span>
          </p>
          <p>Instalaciones en agenda: {agenda.length}</p>
          <p>Última actualización: {ping ? formatDate(ping.estado?.actualizado_en ?? new Date()) : "—"}</p>
        </div>
      </article>
    </section>
  );
}
