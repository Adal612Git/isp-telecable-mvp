import { FormEvent, useMemo, useState } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

interface Plan {
  id: string;
  nombre: string;
  precio: number;
  velocidad: string;
  descripcion: string;
}

interface Propuesta {
  id: string;
  cliente: string;
  planId: string;
  notas: string;
  creadaEn: string;
}

const planes: Plan[] = [
  {
    id: "INT100",
    nombre: "Internet 100",
    precio: 299,
    velocidad: "100 Mbps",
    descripcion: "Ideal para hogares pequeños y uso cotidiano."
  },
  {
    id: "INT200",
    nombre: "Internet 200",
    precio: 399,
    velocidad: "200 Mbps",
    descripcion: "Videollamadas, streaming HD y dispositivos simultáneos."
  },
  {
    id: "INT500",
    nombre: "Internet 500",
    precio: 599,
    velocidad: "500 Mbps",
    descripcion: "Empresas y creadores de contenido con alta demanda."
  }
];

function formatCurrency(value: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

function VentasHome({
  propuestas,
  onNuevaPropuesta
}: {
  propuestas: Propuesta[];
  onNuevaPropuesta: (propuesta: Omit<Propuesta, "id" | "creadaEn">) => void;
}) {
  const [cliente, setCliente] = useState("");
  const [planId, setPlanId] = useState(planes[0]?.id ?? "");
  const [notas, setNotas] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);

  const planSeleccionado = useMemo(() => planes.find((plan) => plan.id === planId), [planId]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!cliente.trim()) {
      setMensaje("Ingresa el nombre del cliente para generar la propuesta.");
      return;
    }
    onNuevaPropuesta({ cliente: cliente.trim(), planId, notas: notas.trim() });
    setMensaje(`Propuesta creada para ${cliente.trim()} · ${planId}`);
    setCliente("");
    setNotas("");
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <section className="glass card-border rounded-3xl border border-slate-800/60 bg-slate-900/50 p-6 shadow-xl lg:col-span-3">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Propuesta rápida</p>
          <h2 className="text-2xl font-semibold text-slate-100">Genera una oferta personalizada</h2>
          <p className="mt-2 text-sm text-slate-400">
            Selecciona el plan adecuado, añade notas y envía el resumen al cliente.
          </p>
        </header>

        {mensaje && (
          <div className="mb-4 rounded-2xl border border-primary/40 bg-primary/10 px-4 py-3 text-sm text-primary">{mensaje}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5 text-sm text-slate-200">
          <label className="flex flex-col gap-2">
            <span className="text-xs uppercase tracking-wide text-slate-400">Nombre del cliente</span>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-2 outline-none focus:border-primary"
              placeholder="Ej. Ana Martínez"
              value={cliente}
              onChange={(event) => setCliente(event.target.value)}
            />
          </label>

          <div className="space-y-2">
            <span className="text-xs uppercase tracking-wide text-slate-400">Selecciona un plan</span>
            <div className="grid gap-3 md:grid-cols-3">
              {planes.map((plan) => (
                <button
                  key={plan.id}
                  type="button"
                  onClick={() => setPlanId(plan.id)}
                  className={`rounded-2xl border px-4 py-4 text-left transition ${
                    planId === plan.id
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-slate-800 bg-slate-900/60 hover:border-primary"
                  }`}
                >
                  <span className="text-xs uppercase tracking-wide text-slate-400">{plan.id}</span>
                  <strong className="mt-1 block text-lg text-slate-100">{plan.nombre}</strong>
                  <span className="block text-sm text-slate-400">{plan.velocidad}</span>
                  <span className="mt-2 block text-sm font-semibold text-slate-100">{formatCurrency(plan.precio)}</span>
                </button>
              ))}
            </div>
          </div>

          <label className="flex flex-col gap-2">
            <span className="text-xs uppercase tracking-wide text-slate-400">Notas para el cliente</span>
            <textarea
              className="min-h-[120px] rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-3 outline-none focus:border-primary"
              placeholder="Describe beneficios adicionales, descuentos o fechas de instalación estimadas."
              value={notas}
              onChange={(event) => setNotas(event.target.value)}
            />
          </label>

          {planSeleccionado && (
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 text-xs text-slate-300">
              <p className="text-slate-400">Resumen</p>
              <p>
                Plan <strong>{planSeleccionado.nombre}</strong> · {planSeleccionado.velocidad} · {" "}
                <strong>{formatCurrency(planSeleccionado.precio)}</strong>/mes
              </p>
            </div>
          )}

          <button
            type="submit"
            className="rounded-full bg-primary px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-primary-dark"
          >
            Generar propuesta
          </button>
        </form>
      </section>

      <aside className="glass card-border rounded-3xl border border-slate-800/60 bg-slate-900/40 p-6 shadow-xl lg:col-span-2">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Propuestas</p>
            <h3 className="text-lg font-semibold text-slate-100">Seguimiento reciente</h3>
          </div>
          <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{propuestas.length}</span>
        </header>
        <div className="space-y-4 text-sm">
          {propuestas.length ? (
            propuestas.map((propuesta) => {
              const plan = planes.find((item) => item.id === propuesta.planId);
              return (
                <article key={propuesta.id} className="rounded-2xl border border-slate-800/60 bg-slate-950/40 p-4">
                  <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
                    <span>#{propuesta.id}</span>
                    <span>{new Date(propuesta.creadaEn).toLocaleString("es-MX")}</span>
                  </div>
                  <h4 className="mt-2 text-base font-semibold text-slate-100">{propuesta.cliente}</h4>
                  <p className="text-xs text-slate-400">Plan {plan?.nombre ?? propuesta.planId}</p>
                  {propuesta.notas && <p className="mt-2 text-xs text-slate-300">{propuesta.notas}</p>}
                </article>
              );
            })
          ) : (
            <p className="text-sm text-slate-500">
              Aún no tienes propuestas generadas. Completa el formulario para crear la primera.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}

export default function App() {
  const [propuestas, setPropuestas] = useState<Propuesta[]>([]);

  const handleNuevaPropuesta = (base: Omit<Propuesta, "id" | "creadaEn">) => {
    const nueva: Propuesta = {
      ...base,
      id: (propuestas.length + 1).toString().padStart(3, "0"),
      creadaEn: new Date().toISOString()
    };
    setPropuestas((prev) => [nueva, ...prev]);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase text-slate-500">Telecable MVP</p>
            <h1 className="text-lg font-semibold text-primary">Portal de Ventas</h1>
          </div>
          <nav className="text-sm">
            <NavLink
              to="/ventas"
              className={({ isActive }) =>
                [
                  "rounded-full px-4 py-2 transition",
                  isActive ? "bg-primary text-slate-950" : "text-slate-400 hover:text-slate-100"
                ].join(" ")
              }
            >
              Dashboard
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-6">
        <Routes>
          <Route
            path="/ventas"
            element={<VentasHome propuestas={propuestas} onNuevaPropuesta={handleNuevaPropuesta} />}
          />
          <Route path="/" element={<Navigate to="/ventas" replace />} />
        </Routes>
      </main>

      <footer className="border-t border-slate-800/60 bg-slate-950/80 px-6 py-6 text-center text-xs text-slate-500">
        Diseñado para habilitar demos rápidas de equipos comerciales.
      </footer>
    </div>
  );
}
