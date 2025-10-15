import type { RouterSummary, RouterPowerAction } from "../api";
import { formatDate } from "../utils";

interface Props {
  routers: RouterSummary[];
  loading: boolean;
  onRefresh: () => Promise<void>;
  onAction: (routerId: string, action: RouterPowerAction) => Promise<void>;
}

function formatUptime(seconds: number | undefined) {
  if (!seconds || Number.isNaN(seconds)) return "0s";
  const total = Math.floor(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const parts: string[] = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  parts.push(`${secs}s`);
  return parts.join(" ");
}

export default function RoutersPage({ routers, loading, onRefresh, onAction }: Props) {
  return (
    <section className="glass card-border rounded-3xl border border-slate-800/70 bg-slate-900/40 p-6 shadow-xl">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Simulador</p>
          <h2 className="text-2xl font-semibold text-slate-100">Routers provisionados</h2>
          <p className="mt-2 text-sm text-slate-400">
            Monitorea el estado en vivo del microservicio y ejecuta acciones remotas para los clientes.
          </p>
        </div>
        <button
          onClick={() => void onRefresh()}
          disabled={loading}
          className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Actualizando..." : "Refrescar"}
        </button>
      </header>

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">Router</th>
              <th className="px-3 py-2 font-medium">Cliente</th>
              <th className="px-3 py-2 font-medium">Estado</th>
              <th className="px-3 py-2 font-medium">Uptime</th>
              <th className="px-3 py-2 font-medium">IP</th>
              <th className="px-3 py-2 font-medium">Último cambio</th>
              <th className="px-3 py-2 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {routers.map((router) => {
              const isOn = router.state === "on";
              return (
                <tr key={router.router_id} className="border-t border-slate-800/70">
                  <td className="px-3 py-3 text-xs font-semibold text-slate-100">{router.router_id}</td>
                  <td className="px-3 py-3 text-xs text-slate-300">{router.cliente_id ?? "—"}</td>
                  <td className="px-3 py-3 text-xs">
                    <span
                      className={`rounded-full px-3 py-1 font-semibold ${
                        isOn ? "bg-emerald-500/20 text-emerald-200" : "bg-rose-500/20 text-rose-200"
                      }`}
                    >
                      {isOn ? "Encendido" : "Apagado"}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-300">{formatUptime(router.uptime)}</td>
                  <td className="px-3 py-3 text-xs text-slate-300">{router.ip}</td>
                  <td className="px-3 py-3 text-xs text-slate-400">{formatDate(router.last_state_change)}</td>
                  <td className="px-3 py-3 text-xs">
                    <div className="flex flex-wrap gap-2">
                      <button
                        className={`rounded-full px-3 py-1 font-semibold transition ${
                          isOn
                            ? "border border-rose-400 text-rose-200 hover:bg-rose-400/10"
                            : "border border-emerald-400 text-emerald-200 hover:bg-emerald-400/10"
                        }`}
                        onClick={() => void onAction(router.router_id, isOn ? "off" : "on")}
                        disabled={loading}
                      >
                        {isOn ? "Apagar" : "Encender"}
                      </button>
                      <button
                        className="rounded-full border border-slate-700 px-3 py-1 font-semibold text-slate-200 transition hover:border-primary hover:text-primary"
                        onClick={() => void onAction(router.router_id, "reboot")}
                        disabled={loading}
                      >
                        Reiniciar
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {!routers.length && (
              <tr>
                <td className="px-3 py-6 text-center text-xs text-slate-500" colSpan={7}>
                  No hay routers disponibles. Registra un cliente desde el portal para provisionar uno nuevo.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
