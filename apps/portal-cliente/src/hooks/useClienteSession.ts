import { useEffect, useState } from "react";

const STORAGE_KEY = "telecable:cliente-id";

export function useClienteSession() {
  const [clienteId, setClienteId] = useState<number | null>(() => {
    const stored = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    return stored ? Number(stored) : null;
  });

  useEffect(() => {
    if (clienteId && !Number.isNaN(clienteId)) {
      localStorage.setItem(STORAGE_KEY, String(clienteId));
    }
  }, [clienteId]);

  function update(id: number) {
    if (!Number.isNaN(id) && id > 0) {
      setClienteId(id);
    }
  }

  function clear() {
    localStorage.removeItem(STORAGE_KEY);
    setClienteId(null);
  }

  return { clienteId, update, clear };
}
