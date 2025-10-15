import { createContext, useContext } from "react";
import type {
  ClientSummary,
  FacturaSummary,
  PagoSummary,
  TicketSummary,
  InstalacionSummary,
  RouterStatus
} from "../api/http";

export interface PortalData {
  cliente: ClientSummary | null;
  facturas: FacturaSummary[];
  pagos: PagoSummary[];
  tickets: TicketSummary[];
  instalaciones: InstalacionSummary[];
  router: RouterStatus | null;
  zona: string | null;
}

export const PortalDataContext = createContext<PortalData>({
  cliente: null,
  facturas: [],
  pagos: [],
  tickets: [],
  instalaciones: [],
  router: null,
  zona: null
});

export function usePortalData(): PortalData {
  return useContext(PortalDataContext);
}

