import { useTechnician } from "../context";

interface Props {
  loading: boolean;
}

export default function InventarioPage({ loading }: Props) {
  const { inventario, zona } = useTechnician();
  const disponible =
    inventario && typeof inventario === "object" && "ok" in (inventario as Record<string, unknown>)
      ? Boolean((inventario as Record<string, unknown>).ok)
      : false;
  const faltante =
    inventario && typeof inventario === "object" && "missing" in (inventario as Record<string, unknown>)
      ? String((inventario as Record<string, unknown>).missing)
      : null;

  return (
    <section className="card">
      <h2 className="text-lg font-semibold">Inventario crítico</h2>
      <p className="mt-2 text-sm text-slate-400">
        Consulta la disponibilidad básica para la zona asignada. El servicio de inventario responde en modo emulado.
      </p>
      <div className="mt-4 rounded border border-slate-800/70 bg-slate-900/60 px-4 py-4 text-sm text-slate-300">
        <p>Zona: {zona ?? "N/A"}</p>
        <p className="mt-2">Estado: {disponible ? "Disponible" : "En revisión"}</p>
        {faltante && <p className="mt-2 text-xs text-amber-300">Faltante: {faltante}</p>}
        {loading && <p className="mt-3 text-xs text-slate-500">Actualizando…</p>}
      </div>
    </section>
  );
}
