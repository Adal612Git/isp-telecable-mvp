import { usePortalData } from "../context/PortalDataContext";
import { formatCurrency, formatDateTime } from "../utils/format";

interface Props {
  loading: boolean;
  onRefresh: () => void;
  onCorte: () => void;
  onReconectar: () => void;
}

export default function DashboardPage({ loading, onRefresh, onCorte, onReconectar }: Props) {
  const { cliente, facturas, pagos, instalaciones, router } = usePortalData();

  return (
    <section className="grid gap-6 md:grid-cols-2">
      <article className="glass card-border rounded-3xl p-6 shadow-xl">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase text-slate-400">Resumen</p>
            <h2 className="text-lg font-semibold text-slate-100">Estado del servicio</h2>
          </div>
          <button
            disabled={loading}
            onClick={onRefresh}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 transition hover:border-primary hover:text-primary disabled:opacity-50"
          >
            Actualizar
          </button>
        </header>

        <div className="mt-6 space-y-4 text-sm text-slate-300">
          <div className="flex justify-between">
            <span>Cliente</span>
            <strong>{cliente ? `${cliente.nombre} · #${cliente.id}` : "—"}</strong>
          </div>
          <div className="flex justify-between">
            <span>Plan</span>
            <strong>{cliente?.plan_id ?? "—"}</strong>
          </div>
          <div className="flex justify-between">
            <span>Estatus</span>
            <span
              className={[
                "rounded-full px-3 py-1 text-xs font-semibold uppercase",
                cliente?.estatus === "activo" ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-200"
              ].join(" ")}
            >
              {cliente?.estatus ?? "desconocido"}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Zona</span>
            <strong>{cliente?.zona ?? "—"}</strong>
          </div>
        </div>

        <footer className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={onReconectar}
            className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-primary-dark"
          >
            Reconectar servicio
          </button>
          <button
            onClick={onCorte}
            className="rounded-full border border-red-400 px-4 py-2 text-xs font-semibold text-red-200/90 transition hover:bg-red-400/10"
          >
            Suspender temporalmente
          </button>
        </footer>
      </article>

      <article className="glass card-border rounded-3xl p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-100">Estado de red</h2>
        <p className="mt-2 text-sm text-slate-400">
          Visualiza la telemetría del router emulado (modo <code>{router?.modo ?? "N/A"}</code>).
        </p>

        <dl className="mt-6 space-y-3 text-sm text-slate-300">
          <div className="flex justify-between">
            <dt>Conexión</dt>
            <dd className={router?.conectado ? "text-emerald-300" : "text-amber-200"}>
              {router?.conectado ? "Activo" : "Suspendido"}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt>Latencia</dt>
            <dd>{router ? `${router.latencia_ms} ms` : "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt>Dirección IP</dt>
            <dd>{router?.ip ?? "10.0.0.0"}</dd>
          </div>
          <div className="flex justify-between text-xs text-slate-500">
            <dt>Última actualización</dt>
            <dd>{router ? formatDateTime(router.actualizado_en) : "—"}</dd>
          </div>
        </dl>
      </article>

      <article className="glass card-border rounded-3xl p-6 shadow-xl md:col-span-2">
        <h2 className="text-lg font-semibold text-slate-100">Facturación reciente</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-400">
              <tr>
                <th className="px-3 py-2 font-medium">UUID</th>
                <th className="px-3 py-2 font-medium">Total</th>
                <th className="px-3 py-2 font-medium">Estatus</th>
              </tr>
            </thead>
            <tbody>
              {facturas.map((factura) => (
                <tr key={factura.uuid} className="border-t border-slate-800/60">
                  <td className="px-3 py-2 text-xs">{factura.uuid}</td>
                  <td className="px-3 py-2 text-xs">{formatCurrency(factura.total)}</td>
                  <td className="px-3 py-2 text-xs capitalize">{factura.estatus}</td>
                </tr>
              ))}
              {!facturas.length && (
                <tr>
                  <td className="px-3 py-6 text-center text-xs text-slate-500" colSpan={3}>
                    Sin facturas generadas todavía.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>

      <article className="glass card-border rounded-3xl p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-100">Pagos recientes</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          {pagos.map((pago) => (
            <li key={pago.referencia} className="rounded border border-slate-800/70 px-3 py-3">
              <div className="flex items-center justify-between">
                <strong>{pago.metodo.toUpperCase()}</strong>
                <span>{formatCurrency(pago.monto)}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {pago.estatus} · {pago.creadoEn ? formatDateTime(pago.creadoEn) : "sin fecha"}
              </div>
            </li>
          ))}
          {!pagos.length && <li className="text-xs text-slate-500">Sin pagos registrados.</li>}
        </ul>
      </article>

      <article className="glass card-border rounded-3xl p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-100">Instalaciones</h2>
        <ul className="mt-4 space-y-3 text-sm">
          {instalaciones.map((inst) => (
            <li key={inst.id} className="rounded border border-slate-800/70 px-3 py-3">
              <div className="flex items-center justify-between text-xs uppercase text-slate-400">
                <span># {inst.id}</span>
                <span>{inst.estado}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                Ventana {inst.ventana} · {formatDateTime(inst.creadoEn)}
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Evidencias: {inst.evidencias.join(", ") || "sin evidencias"}
              </div>
            </li>
          ))}
          {!instalaciones.length && <li className="text-xs text-slate-500">Sin instalaciones pendientes.</li>}
        </ul>
      </article>
    </section>
  );
}
