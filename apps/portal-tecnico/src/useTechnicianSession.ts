import { useEffect, useState } from "react";

const STORAGE_KEY = "telecable:tecnico";

export function useTechnicianSession() {
  const [zona, setZona] = useState<string | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed?.zona ?? null;
    } catch (error) {
      console.warn("No se pudo recuperar la zona", error);
      return null;
    }
  });

  const [nombre, setNombre] = useState<string | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed?.nombre ?? null;
    } catch (error) {
      return null;
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ zona, nombre }));
  }, [zona, nombre]);

  function setSession(nextZona: string, nextNombre: string) {
    setZona(nextZona);
    setNombre(nextNombre);
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    setZona(null);
    setNombre(null);
  }

  return { zona, nombre, setSession, clearSession };
}
