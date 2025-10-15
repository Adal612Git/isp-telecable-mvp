import { createContext, useContext } from "react";
import type { InstalacionRow, TicketRow, RouterPing, RouterSummary } from "./api";

export interface TechnicianState {
  zona: string | null;
  tecnico: string | null;
  agenda: InstalacionRow[];
  tickets: TicketRow[];
  inventario: unknown;
  ping: RouterPing | null;
  routers: RouterSummary[];
}

export const TechnicianContext = createContext<TechnicianState>({
  zona: null,
  tecnico: null,
  agenda: [],
  tickets: [],
  inventario: null,
  ping: null,
  routers: []
});

export function useTechnician() {
  return useContext(TechnicianContext);
}
