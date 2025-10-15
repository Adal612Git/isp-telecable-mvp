import { FormEvent, useState } from "react";
import { usePortalData } from "../context/PortalDataContext";
import { formatCurrency, formatDateTime } from "../utils/format";

interface Props {
  loading: boolean;
  onRegistrarPago: (payload: { monto: number; metodo: string; to?: string }) => Promise<void>;
}

export default function PaymentsPage({ loading, onRegistrarPago }: Props) {
  const { cliente, pagos } = usePortalData();
  const [monto, setMonto] = useState(299);
  const [metodo, setMetodo] = useState("spei");
  const [whatsapp, setWhatsapp] = useState("5215512345678");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cliente) {
      setStatus("Selecciona primero un cliente.");
      return;
    }
    setStatus("Procesando pago...");
    try {
      await onRegistrarPago({ monto, metodo, to: whatsapp });
      setStatus("Pago conciliado y reconectado ✅");
    } catch (err) {
      console.error(err);
      setStatus("No se pudo procesar el pago. Revisa la consola o los servicios.");
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="glass card-border rounded-3xl p-6">
        <h2 className="text-lg font-semibold text-slate-100">Registrar un pago</h2>
        <p className="mt-2 text-sm text-slate-400">
          Simula el SPEI desde el portal del cliente. Si la infraestructura está activa se invoca el orquestador y se
          notifica al mock de WhatsApp.
        </p>
        <form className="mt-6 space-y-4 text-sm" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-xs uppercase text-slate-400">Monto (MXN)</span>
            <input
              type="number"
              min={1}
              step="0.01"
              value={monto}
              onChange={(event) => setMonto(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-primary"
            />
          </label>
          <label className="block">
            <span className="text-xs uppercase text-slate-400">Método</span>
            <select
              value={metodo}
              onChange={(event) => setMetodo(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-primary"
            >
              <option value="spei">SPEI</option>
              <option value="tarjeta">Tarjeta</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase text-slate-400">WhatsApp para notificación</span>
            <input
              value={whatsapp}
              onChange={(event) => setWhatsapp(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-primary"
            />
          </label>
          <button
            disabled={loading}
            className="w-full rounded-full bg-primary px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-primary-dark disabled:opacity-60"
          >
            {loading ? "Procesando..." : "Pagar y conciliar"}
          </button>
        </form>
        {status && <p className="mt-4 text-xs text-slate-400">{status}</p>}
      </section>

      <section className="glass card-border rounded-3xl p-6">
        <h2 className="text-lg font-semibold text-slate-100">Historial</h2>
        <ul className="mt-4 space-y-3 text-sm">
          {pagos.map((pago) => (
            <li key={pago.referencia} className="rounded border border-slate-800/70 px-3 py-3">
              <div className="flex items-center justify-between">
                <strong>{pago.metodo.toUpperCase()}</strong>
                <span>{formatCurrency(pago.monto)}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {pago.estatus} · {pago.creadoEn ? formatDateTime(pago.creadoEn) : "sin fecha"}
              </div>
              <div className="text-xs text-slate-600">Referencia: {pago.referencia}</div>
            </li>
          ))}
          {!pagos.length && (
            <li className="text-xs text-slate-500">No hay pagos registrados. Usa el formulario para generar uno.</li>
          )}
        </ul>
      </section>
    </div>
  );
}
