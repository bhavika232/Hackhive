import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { checkHealth, getIncidents, type Incident } from '../services/api';
interface IncidentStore {
  incidents: Incident[]; loading: boolean; error: string | null;
  health: 'checking' | 'connected' | 'disconnected'; healthError: string | null;
  checkedAt: Date | null; loadedAt: Date | null; refresh: () => void;
  selectedId: number | null; openIncident: (id: number) => void; closeIncident: () => void;
  updateIncident: (incident: Incident) => void;
}
const Context = createContext<IncidentStore | null>(null);
export function IncidentProvider({ children }: { children: ReactNode }) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<IncidentStore['health']>('checking');
  const [healthError, setHealthError] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const active = useRef<AbortController>();
  const refresh = useCallback(() => {
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    setLoading(true); setHealth('checking');
    void Promise.allSettled([checkHealth(controller.signal), getIncidents(controller.signal)]).then(([healthResult, dataResult]) => {
      if (controller.signal.aborted) return;
      setHealth(healthResult.status === 'fulfilled' ? 'connected' : 'disconnected');
      setHealthError(healthResult.status === 'rejected' ? String(healthResult.reason?.message ?? 'Health check failed') : null);
      setCheckedAt(new Date());
      if (dataResult.status === 'fulfilled' && Array.isArray(dataResult.value)) {
        setIncidents(dataResult.value); setError(null); setLoadedAt(new Date());
      } else setError(dataResult.status === 'rejected' ? String(dataResult.reason?.message ?? 'Unable to load incidents') : 'The backend returned an invalid incident list.');
      setLoading(false);
    });
  }, []);
  useEffect(() => { refresh(); return () => active.current?.abort(); }, [refresh]);
  const updateIncident = (incident: Incident) => {
    setIncidents(current => current.map(i => i.incident_id === incident.incident_id ? incident : i));
  };
  return <Context.Provider value={{ incidents, loading, error, health, healthError, checkedAt, loadedAt, refresh, selectedId,
    openIncident: setSelectedId, closeIncident: () => setSelectedId(null), updateIncident }}>{children}</Context.Provider>;
}
export function useIncidents() {
  const value = useContext(Context); if (!value) throw new Error('IncidentProvider is required'); return value;
}
