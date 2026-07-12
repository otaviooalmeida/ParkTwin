import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, AlertCircle, Camera, CircleDot, RefreshCw, Timer } from 'lucide-react';
import './styles.css';

type SpotStatus = 'free' | 'occupied' | 'uncertain';

type SpotState = {
  id: string;
  status: SpotStatus;
  confidence: number | null;
  occupied_since: string | null;
  last_changed_at: string | null;
};

type Snapshot = {
  timestamp: string;
  parking_lot_id: string | null;
  spots: SpotState[];
  total_spots: number;
  occupied_count: number;
  free_count: number;
  uncertain_count: number;
  occupancy_rate: number;
};

type HistoryRow = {
  timestamp: string;
  occupied_count: number;
  free_count: number;
  uncertain_count: number;
  occupancy_rate: number;
};

type SpotEvent = {
  snapshot_timestamp: string;
  spot_id: string;
  status: SpotStatus;
  confidence: number | null;
  created_at: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [events, setEvents] = useState<SpotEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageVersion, setImageVersion] = useState(Date.now());

  async function loadDashboard() {
    setError(null);
    try {
      const [snapshotResponse, historyResponse, eventsResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/api/snapshots/latest`),
        fetch(`${apiBaseUrl}/api/history`),
        fetch(`${apiBaseUrl}/api/events?limit=20`),
      ]);

      if (!snapshotResponse.ok) {
        throw new Error('Nenhum snapshot disponível.');
      }

      setSnapshot(await snapshotResponse.json());
      setHistory(historyResponse.ok ? await historyResponse.json() : []);
      setEvents(eventsResponse.ok ? await eventsResponse.json() : []);
      setImageVersion(Date.now());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar dados.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
    const timer = window.setInterval(loadDashboard, 5000);
    return () => window.clearInterval(timer);
  }, []);

  const latestHistory = useMemo(() => history.slice(-12), [history]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ParkTwin</p>
          <h1>Operação do estacionamento</h1>
        </div>
        <button className="icon-button" onClick={loadDashboard} aria-label="Atualizar dados">
          <RefreshCw size={18} />
        </button>
      </header>

      {error && (
        <section className="notice" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </section>
      )}

      <section className="metrics-grid" aria-label="Métricas atuais">
        <Metric icon={<CircleDot size={18} />} label="Total" value={snapshot?.total_spots ?? '-'} />
        <Metric icon={<Activity size={18} />} label="Ocupadas" value={snapshot?.occupied_count ?? '-'} />
        <Metric icon={<Camera size={18} />} label="Livres" value={snapshot?.free_count ?? '-'} />
        <Metric icon={<Timer size={18} />} label="Ocupação" value={snapshot ? `${(snapshot.occupancy_rate * 100).toFixed(1)}%` : '-'} />
      </section>

      <section className="content-grid">
        <div className="image-panel">
          <div className="panel-heading">
            <div>
              <h2>Imagem analisada</h2>
              <p>{snapshot ? formatDate(snapshot.timestamp) : 'Aguardando snapshot'}</p>
            </div>
            {isLoading && <span className="loading">Carregando</span>}
          </div>
          <img
            className="parking-image"
            src={`${apiBaseUrl}/api/images/latest?v=${imageVersion}`}
            alt="Imagem anotada do estacionamento"
          />
        </div>

        <div className="status-panel">
          <div className="panel-heading">
            <div>
              <h2>Vagas</h2>
              <p>{snapshot?.parking_lot_id ?? 'default'}</p>
            </div>
          </div>
          <div className="spot-list">
            {(snapshot?.spots ?? []).map((spot) => (
              <div className="spot-row" key={spot.id}>
                <span className="spot-id">{spot.id}</span>
                <StatusBadge status={spot.status} />
                <span className="confidence">{formatConfidence(spot.confidence)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bottom-grid">
        <div className="history-panel">
          <div className="panel-heading">
            <div>
              <h2>Histórico</h2>
              <p>Últimas leituras</p>
            </div>
          </div>
          <div className="bar-chart">
            {latestHistory.map((row) => (
              <div className="bar-item" key={row.timestamp} title={formatDate(row.timestamp)}>
                <span style={{ height: `${Math.max(row.occupancy_rate * 100, 4)}%` }} />
              </div>
            ))}
          </div>
        </div>

        <div className="events-panel">
          <div className="panel-heading">
            <div>
              <h2>Eventos recentes</h2>
              <p>Últimas mudanças registradas</p>
            </div>
          </div>
          <div className="event-list">
            {events.map((event, index) => (
              <div className="event-row" key={`${event.spot_id}-${event.created_at}-${index}`}>
                <span className="spot-id">{event.spot_id}</span>
                <StatusBadge status={event.status} />
                <time>{formatDate(event.created_at)}</time>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ status }: { status: SpotStatus }) {
  const labels: Record<SpotStatus, string> = {
    free: 'Livre',
    occupied: 'Ocupada',
    uncertain: 'Incerta',
  };

  return <span className={`status-badge ${status}`}>{labels[status]}</span>;
}

function formatConfidence(value: number | null) {
  if (value === null || value === undefined) {
    return '-';
  }

  return `${(value * 100).toFixed(0)}%`;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

createRoot(document.getElementById('root')!).render(<App />);
