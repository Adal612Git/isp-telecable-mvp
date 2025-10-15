import { FormEvent, useMemo, useState } from "react";
import type {
  ClienteCreatePayload,
  ClientSummary,
  RouterPowerAction,
  RouterStatus
} from "../api/http";
import { formatDateTime } from "../utils/format";

const planes = [
  { id: "INT100", nombre: "Internet 100", descripcion: "Velocidad simétrica 100 Mbps" },
  { id: "INT200", nombre: "Internet 200", descripcion: "Ideal para streaming y home office" },
  { id: "INT500", nombre: "Internet 500", descripcion: "Conexión ultra rápida para gamers" }
];

const zonas = ["NORTE", "SUR", "CENTRO"];

interface Props {
  loading: boolean;
  cliente: ClientSummary | null;
  router: RouterStatus | null;
  onRegister: (payload: ClienteCreatePayload) => Promise<ClientSummary>;
  onPower: (action: RouterPowerAction) => Promise<void>;
  streamMode: "idle" | "ws" | "polling";
  globalError: string | null;
}

const initialForm: ClienteCreatePayload = {
  nombre: "",
  rfc: "",
  email: "",
  telefono: "",
  plan_id: "INT100",
  domicilio: {
    calle: "",
    numero: "",
    colonia: "",
    cp: "",
    ciudad: "",
    estado: "",
    zona: zonas[0]
  },
  contacto: {
    nombre: "",
    email: "",
    telefono: ""
  },
  consentimiento: {
    marketing: false,
    terminos: true
  }
};

function formatUptime(seconds: number | undefined) {
  if (!seconds || Number.isNaN(seconds)) {
    return "0s";
  }
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  parts.push(`${secs}s`);
  return parts.join(" ");
}

const streamDescriptions: Record<Props["streamMode"], string> = {
  idle: "Esperando actividad",
  ws: "WebSocket en vivo",
  polling: "Actualización cada 2s"
};

export default function MiRouterPage({
  loading,
  cliente,
  router,
  onRegister,
  onPower,
  streamMode,
  globalError
}: Props) {
  const [form, setForm] = useState<ClienteCreatePayload>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [powerLoading, setPowerLoading] = useState(false);

  const titularPreview = useMemo(() => {
    if (!cliente) return "—";
    return `${cliente.nombre} · #${cliente.id}`;
  }, [cliente]);

  const connectionLabel = useMemo(() => {
    if (!router) return "Sin router";
    return router.state === "on" ? "Conectado" : "Apagado";
  }, [router]);

  const connectionTone = router?.state === "on" ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-200";

  const handleChange = <K extends keyof ClienteCreatePayload>(key: K, value: ClienteCreatePayload[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleAddressChange = <K extends keyof ClienteCreatePayload["domicilio"]>(
    key: K,
    value: ClienteCreatePayload["domicilio"][K]
  ) => {
    setForm((prev) => ({ ...prev, domicilio: { ...prev.domicilio, [key]: value } }));
  };

  const handleContactChange = <K extends keyof ClienteCreatePayload["contacto"]>(
    key: K,
    value: ClienteCreatePayload["contacto"][K]
  ) => {
    setForm((prev) => ({ ...prev, contacto: { ...prev.contacto, [key]: value } }));
  };

  const autofillDemo = () => {
    const now = Date.now();
    const email = `cliente.demo${now % 1000}@telecable.test`;
    setForm({
      nombre: "Cliente Demo",
      rfc: "DEMO800101AA1",
      email,
      telefono: "+52 5512345678",
      plan_id: "INT200",
      domicilio: {
        calle: "Av. Siempre Viva",
        numero: "742",
        colonia: "Centro",
        cp: "01010",
        ciudad: "CDMX",
        estado: "CDMX",
        zona: zonas[1]
      },
      contacto: {
        nombre: "Cliente Demo",
        email,
        telefono: "+52 5512345678"
      },
      consentimiento: {
        marketing: true,
        terminos: true
      }
    });
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    setSuccessMessage(null);

    if (!form.nombre || !form.rfc || !form.email || !form.telefono) {
      setLocalError("Completa los datos principales del titular.");
      return;
    }
    if (!form.consentimiento.terminos) {
      setLocalError("Debes aceptar los términos y condiciones para continuar.");
      return;
    }

    setSubmitting(true);
    try {
      const payload: ClienteCreatePayload = {
        ...form,
        contacto: {
          nombre: form.contacto.nombre || form.nombre,
          email: form.contacto.email || form.email,
          telefono: form.contacto.telefono || form.telefono
        }
      };
      const nuevo = await onRegister(payload);
      setSuccessMessage(
        `Cliente ${nuevo.nombre} (#${nuevo.id}) creado. Router ${nuevo.router_id ?? "pendiente"} asociado automáticamente.`
      );
      setForm(initialForm);
    } catch (err) {
      console.error(err);
      setLocalError("No se pudo registrar el cliente. Intenta nuevamente.");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePowerClick = async (action: RouterPowerAction) => {
    setLocalError(null);
    setPowerLoading(true);
    try {
      await onPower(action);
    } catch (err) {
      console.error(err);
      setLocalError("No se pudo ejecutar la acción sobre el router.");
    } finally {
      setPowerLoading(false);
    }
  };

  const logs = (router?.logs ?? []).slice().reverse();

  return (
    <section className="grid gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="glass card-border rounded-3xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-xl lg:col-span-3">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Alta de cliente</p>
            <h2 className="text-2xl font-semibold text-slate-100">Registra un nuevo servicio</h2>
            <p className="mt-2 text-sm text-slate-400">
              Al completar el registro se provisiona un router virtual y se enlaza automáticamente al titular.
            </p>
          </div>
          <button
            type="button"
            onClick={autofillDemo}
            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 transition hover:border-primary hover:text-primary"
          >
            Autocompletar demo
          </button>
        </header>

        {(localError || globalError) && (
          <div className="mb-4 rounded-2xl border border-rose-500/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {localError || globalError}
          </div>
        )}
        {successMessage && (
          <div className="mb-4 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            {successMessage}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Nombre completo</span>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm outline-none focus:border-primary"
              value={form.nombre}
              onChange={(event) => handleChange("nombre", event.target.value)}
              placeholder="Nombre del titular"
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">RFC</span>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm uppercase outline-none focus:border-primary"
              value={form.rfc}
              onChange={(event) => handleChange("rfc", event.target.value.toUpperCase())}
              placeholder="RFC"
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Email</span>
            <input
              type="email"
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm outline-none focus:border-primary"
              value={form.email}
              onChange={(event) => handleChange("email", event.target.value)}
              placeholder="correo@ejemplo.com"
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Teléfono</span>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm outline-none focus:border-primary"
              value={form.telefono}
              onChange={(event) => handleChange("telefono", event.target.value)}
              placeholder="+52 55 1234 5678"
              required
            />
          </label>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <span className="text-xs uppercase tracking-wide text-slate-400">Plan</span>
            <div className="grid gap-3">
              {planes.map((plan) => (
                <label
                  key={plan.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3 text-sm transition ${
                    form.plan_id === plan.id ? "border-primary bg-primary/10" : "border-slate-800 hover:border-primary"
                  }`}
                >
                  <input
                    type="radio"
                    name="plan"
                    value={plan.id}
                    checked={form.plan_id === plan.id}
                    onChange={() => handleChange("plan_id", plan.id)}
                    className="mt-1"
                  />
                  <span>
                    <strong className="block text-slate-100">{plan.nombre}</strong>
                    <span className="text-slate-400">{plan.descripcion}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <span className="text-xs uppercase tracking-wide text-slate-400">Zona de instalación</span>
            <div className="flex flex-wrap gap-2">
              {zonas.map((zona) => (
                <button
                  type="button"
                  key={zona}
                  className={`rounded-full px-4 py-2 text-xs font-semibold transition ${
                    form.domicilio.zona === zona ? "bg-primary text-slate-950" : "border border-slate-700 text-slate-300"
                  }`}
                  onClick={() => handleAddressChange("zona", zona)}
                >
                  {zona}
                </button>
              ))}
            </div>
            <div className="grid gap-3 text-sm">
              <input
                className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
                placeholder="Calle"
                value={form.domicilio.calle}
                onChange={(event) => handleAddressChange("calle", event.target.value)}
                required
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
                  placeholder="Número"
                  value={form.domicilio.numero}
                  onChange={(event) => handleAddressChange("numero", event.target.value)}
                  required
                />
                <input
                  className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
                  placeholder="CP"
                  value={form.domicilio.cp}
                  onChange={(event) => handleAddressChange("cp", event.target.value)}
                  required
                />
              </div>
              <input
                className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
                placeholder="Colonia"
                value={form.domicilio.colonia}
                onChange={(event) => handleAddressChange("colonia", event.target.value)}
                required
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
                  placeholder="Ciudad"
                  value={form.domicilio.ciudad}
                  onChange={(event) => handleAddressChange("ciudad", event.target.value)}
                  required
                />
                <input
                  className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
                  placeholder="Estado"
                  value={form.domicilio.estado}
                  onChange={(event) => handleAddressChange("estado", event.target.value)}
                  required
                />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Contacto de referencia</span>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm outline-none focus:border-primary"
              placeholder="Nombre del contacto"
              value={form.contacto.nombre}
              onChange={(event) => handleContactChange("nombre", event.target.value)}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm outline-none focus:border-primary"
              placeholder="Email de contacto"
              value={form.contacto.email}
              onChange={(event) => handleContactChange("email", event.target.value)}
            />
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm outline-none focus:border-primary"
              placeholder="Teléfono contacto"
              value={form.contacto.telefono}
              onChange={(event) => handleContactChange("telefono", event.target.value)}
            />
          </div>
        </div>

        <label className="mt-6 flex items-center gap-3 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={form.consentimiento.terminos}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                consentimiento: { ...prev.consentimiento, terminos: event.target.checked }
              }))
            }
            className="h-5 w-5 rounded border border-slate-700 bg-slate-900"
          />
          Acepto términos y condiciones del servicio y la simulación del router.
        </label>
        <label className="mt-2 flex items-center gap-3 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={form.consentimiento.marketing}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                consentimiento: { ...prev.consentimiento, marketing: event.target.checked }
              }))
            }
            className="h-5 w-5 rounded border border-slate-700 bg-slate-900"
          />
          Deseo recibir promociones personalizadas.
        </label>

        <footer className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-500">
            Titular actual: <span className="font-semibold text-slate-300">{titularPreview}</span>
          </div>
          <button
            type="submit"
            disabled={submitting || loading}
            className="rounded-full bg-primary px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Registrando..." : "Registrar cliente"}
          </button>
        </footer>
      </form>

      <aside className="glass card-border flex h-fit flex-col gap-4 rounded-3xl border border-slate-800/80 bg-slate-900/30 p-6 shadow-xl lg:col-span-2">
        <header className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Mi router</p>
            <h3 className="text-xl font-semibold text-slate-100">Estado en tiempo real</h3>
            <p className="mt-1 text-xs text-slate-400">{streamDescriptions[streamMode]}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${connectionTone}`}>
            {connectionLabel}
          </span>
        </header>

        <div className="grid gap-3 text-sm text-slate-300">
          <div className="flex justify-between">
            <span>ID router</span>
            <strong>{router?.router_id ?? "—"}</strong>
          </div>
          <div className="flex justify-between">
            <span>IP</span>
            <strong>{router?.ip ?? "10.10.x.x"}</strong>
          </div>
          <div className="flex justify-between">
            <span>Uptime</span>
            <strong>{formatUptime(router?.uptime)}</strong>
          </div>
          <div className="flex justify-between text-xs text-slate-500">
            <span>Último cambio</span>
            <span>{router?.last_state_change ? formatDateTime(router.last_state_change) : "—"}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!router || powerLoading}
            onClick={() => handlePowerClick(router?.state === "on" ? "off" : "on")}
            className={`flex-1 rounded-full px-4 py-2 text-sm font-semibold transition ${
              router?.state === "on"
                ? "border border-rose-400 text-rose-200 hover:bg-rose-400/10"
                : "bg-emerald-400 text-slate-950 hover:bg-emerald-300"
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            {powerLoading ? "Procesando..." : router?.state === "on" ? "Apagar" : "Encender"}
          </button>
          <button
            type="button"
            disabled={!router || powerLoading}
            onClick={() => handlePowerClick("reboot")}
            className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-60"
          >
            {powerLoading ? "Procesando..." : "Reiniciar"}
          </button>
        </div>

        <div className="mt-4">
          <h4 className="text-sm font-semibold text-slate-200">Bitácora</h4>
          <div className="mt-2 max-h-56 space-y-3 overflow-y-auto rounded-2xl border border-slate-800/60 bg-slate-950/40 p-4 text-xs">
            {logs.length ? (
              logs.map((log, index) => (
                <div key={`${log.timestamp}-${index}`} className="space-y-1">
                  <div className="text-slate-400">{formatDateTime(log.timestamp)}</div>
                  <p className="text-slate-200">{log.message}</p>
                </div>
              ))
            ) : (
              <p className="text-slate-500">Sin eventos registrados aún.</p>
            )}
          </div>
        </div>
      </aside>
    </section>
  );
}
