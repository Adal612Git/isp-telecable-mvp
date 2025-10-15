import { usePortalData } from "../context/PortalDataContext";
import { formatCurrency } from "../utils/format";

interface Props {
  loading: boolean;
}

export default function ProfilePage({ loading }: Props) {
  const { cliente, facturas, zona } = usePortalData();

  return (
    <div className="glass card-border rounded-3xl p-6">
      <h2 className="text-lg font-semibold text-slate-100">Perfil del cliente</h2>
      {!cliente && (
        <p className="mt-4 text-sm text-slate-400">
          Consulta primero un cliente para visualizar su información o utiliza el demo con ID 1.
        </p>
      )}
      {cliente && (
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold uppercase text-slate-400">Datos de contacto</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              <li>
                <span className="text-slate-500">Nombre:</span> {cliente.nombre}
              </li>
              <li>
                <span className="text-slate-500">RFC:</span> {cliente.rfc}
              </li>
              <li>
                <span className="text-slate-500">Correo:</span> {cliente.email}
              </li>
              <li>
                <span className="text-slate-500">Teléfono:</span> {cliente.telefono}
              </li>
              <li>
                <span className="text-slate-500">Zona:</span> {zona ?? cliente.zona ?? "—"}
              </li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold uppercase text-slate-400">Plan contratado</h3>
            <p className="mt-3 text-sm text-slate-300">
              Plan <strong>{cliente.plan_id ?? "sin plan activo"}</strong>
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Los precios y características se obtienen del servicio Catálogo. Puedes extender esta vista para mostrar
              más detalles en la demo.
            </p>
          </div>
          <div className="md:col-span-2">
            <h3 className="text-sm font-semibold uppercase text-slate-400">Facturación</h3>
            <table className="mt-3 min-w-full text-left text-xs text-slate-400">
              <thead>
                <tr>
                  <th className="px-3 py-2 font-medium">UUID</th>
                  <th className="px-3 py-2 font-medium">Total</th>
                  <th className="px-3 py-2 font-medium">Estatus</th>
                </tr>
              </thead>
              <tbody>
                {facturas.map((factura) => (
                  <tr key={factura.uuid} className="border-t border-slate-800/60">
                    <td className="px-3 py-2">{factura.uuid}</td>
                    <td className="px-3 py-2">{formatCurrency(factura.total)}</td>
                    <td className="px-3 py-2 capitalize">{factura.estatus}</td>
                  </tr>
                ))}
                {!facturas.length && (
                  <tr>
                    <td colSpan={3} className="px-3 py-4 text-center text-slate-500">
                      No hay facturas registradas.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {loading && <p className="mt-4 text-xs text-slate-500">Cargando información…</p>}
    </div>
  );
}
