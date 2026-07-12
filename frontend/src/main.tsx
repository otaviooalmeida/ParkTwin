import React, { ChangeEvent, MouseEvent, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, AlertCircle, Camera, Check, CircleDot, MousePointer2, RefreshCw, Save, Timer, Upload } from 'lucide-react';
import './styles.css';

type ViewMode = 'monitor' | 'setup' | 'process';
type SpotStatus = 'free' | 'occupied' | 'uncertain';
type Point = [number, number];

type ParkingSpotConfig = {
  id: string;
  polygon: Point[];
};

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

type ParkingLotConfig = {
  base_image_exists: boolean;
  base_image_url: string | null;
  spots: ParkingSpotConfig[];
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('monitor');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [events, setEvents] = useState<SpotEvent[]>([]);
  const [config, setConfig] = useState<ParkingLotConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imageVersion, setImageVersion] = useState(Date.now());

  async function loadDashboard() {
    setError(null);
    try {
      const [configResponse, snapshotResponse, historyResponse, eventsResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/api/config`),
        fetch(`${apiBaseUrl}/api/snapshots/latest`),
        fetch(`${apiBaseUrl}/api/history`),
        fetch(`${apiBaseUrl}/api/events?limit=20`),
      ]);

      if (configResponse.ok) {
        setConfig(await configResponse.json());
      }
      setSnapshot(snapshotResponse.ok ? await snapshotResponse.json() : null);
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

  async function uploadBaseImage(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${apiBaseUrl}/api/config/base-image`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      throw new Error(await responseText(response, 'Falha ao enviar imagem base.'));
    }
    setNotice('Imagem base salva.');
    await loadDashboard();
  }

  async function saveSpots(spots: ParkingSpotConfig[]) {
    const response = await fetch(`${apiBaseUrl}/api/config/spots`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spots),
    });
    if (!response.ok) {
      throw new Error(await responseText(response, 'Falha ao salvar vagas.'));
    }
    setNotice('Vagas salvas.');
    await loadDashboard();
  }

  async function processImage(file: File) {
    setIsProcessing(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${apiBaseUrl}/api/process-image`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(await responseText(response, 'Falha ao processar imagem.'));
      }
      const result = await response.json();
      setSnapshot(result.snapshot);
      setNotice('Imagem processada.');
      setViewMode('monitor');
      await loadDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao processar imagem.');
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ParkTwin</p>
          <h1>Operação do estacionamento</h1>
        </div>
        <div className="top-actions">
          <nav className="segmented" aria-label="Modo de trabalho">
            <button className={viewMode === 'monitor' ? 'active' : ''} onClick={() => setViewMode('monitor')}>Monitorar</button>
            <button className={viewMode === 'setup' ? 'active' : ''} onClick={() => setViewMode('setup')}>Configurar</button>
            <button className={viewMode === 'process' ? 'active' : ''} onClick={() => setViewMode('process')}>Processar</button>
          </nav>
          <button className="icon-button" onClick={loadDashboard} aria-label="Atualizar dados">
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      {error && <Notice tone="error" message={error} />}
      {notice && <Notice tone="success" message={notice} />}

      {viewMode === 'monitor' && (
        <MonitorView
          snapshot={snapshot}
          history={history}
          events={events}
          isLoading={isLoading}
          imageVersion={imageVersion}
        />
      )}
      {viewMode === 'setup' && (
        <SetupView
          config={config}
          imageVersion={imageVersion}
          onUploadBaseImage={uploadBaseImage}
          onSaveSpots={saveSpots}
        />
      )}
      {viewMode === 'process' && (
        <ProcessView
          canProcess={Boolean(config?.spots.length)}
          isProcessing={isProcessing}
          onProcessImage={processImage}
        />
      )}
    </main>
  );
}

function MonitorView({ snapshot, history, events, isLoading, imageVersion }: {
  snapshot: Snapshot | null;
  history: HistoryRow[];
  events: SpotEvent[];
  isLoading: boolean;
  imageVersion: number;
}) {
  const latestHistory = useMemo(() => history.slice(-12), [history]);

  return (
    <>
      <section className="metrics-grid" aria-label="Métricas atuais">
        <Metric icon={<CircleDot size={18} />} label="Total" value={snapshot?.total_spots ?? '-'} />
        <Metric icon={<Activity size={18} />} label="Ocupadas" value={snapshot?.occupied_count ?? '-'} />
        <Metric icon={<Camera size={18} />} label="Livres" value={snapshot?.free_count ?? '-'} />
        <Metric icon={<Timer size={18} />} label="Ocupação" value={snapshot ? `${(snapshot.occupancy_rate * 100).toFixed(1)}%` : '-'} />
      </section>

      <section className="content-grid">
        <div className="image-panel">
          <PanelHeading title="Imagem analisada" subtitle={snapshot ? formatDate(snapshot.timestamp) : 'Aguardando snapshot'} right={isLoading ? 'Carregando' : undefined} />
          <img
            className="parking-image"
            src={`${apiBaseUrl}/api/images/latest?v=${imageVersion}`}
            alt="Imagem anotada do estacionamento"
          />
        </div>

        <div className="status-panel">
          <PanelHeading title="Vagas" subtitle={snapshot?.parking_lot_id ?? 'default'} />
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
          <PanelHeading title="Histórico" subtitle="Últimas leituras" />
          <div className="bar-chart">
            {latestHistory.map((row) => (
              <div className="bar-item" key={row.timestamp} title={formatDate(row.timestamp)}>
                <span style={{ height: `${Math.max(row.occupancy_rate * 100, 4)}%` }} />
              </div>
            ))}
          </div>
        </div>

        <div className="events-panel">
          <PanelHeading title="Eventos recentes" subtitle="Últimas mudanças registradas" />
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
    </>
  );
}

function SetupView({ config, imageVersion, onUploadBaseImage, onSaveSpots }: {
  config: ParkingLotConfig | null;
  imageVersion: number;
  onUploadBaseImage: (file: File) => Promise<void>;
  onSaveSpots: (spots: ParkingSpotConfig[]) => Promise<void>;
}) {
  const [spots, setSpots] = useState<ParkingSpotConfig[]>([]);
  const [currentPolygon, setCurrentPolygon] = useState<Point[]>([]);
  const [selectedSpotId, setSelectedSpotId] = useState<string | null>(null);
  const [localImageUrl, setLocalImageUrl] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  const imageUrl = localImageUrl ?? (config?.base_image_exists ? `${apiBaseUrl}/api/config/base-image?v=${imageVersion}` : null);

  useEffect(() => {
    setSpots(config?.spots ?? []);
  }, [config]);

  useEffect(() => {
    if (!imageUrl) return;
    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.onload = () => {
      imageRef.current = image;
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      drawAnnotationCanvas(canvas, image, spots, currentPolygon, selectedSpotId);
    };
    image.src = imageUrl;
  }, [imageUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const image = imageRef.current;
    if (canvas && image) {
      drawAnnotationCanvas(canvas, image, spots, currentPolygon, selectedSpotId);
    }
  }, [spots, currentPolygon, selectedSpotId]);

  function handleCanvasClick(event: MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas || !imageUrl) return;
    const rect = canvas.getBoundingClientRect();
    const point: Point = [
      Math.round((event.clientX - rect.left) * (canvas.width / rect.width)),
      Math.round((event.clientY - rect.top) * (canvas.height / rect.height)),
    ];
    setCurrentPolygon((polygon) => [...polygon, point]);
  }

  function finishSpot() {
    if (currentPolygon.length < 3) return;
    const id = nextSpotId(spots);
    setSpots((items) => [...items, { id, polygon: currentPolygon }]);
    setCurrentPolygon([]);
    setSelectedSpotId(id);
  }

  function deleteSelected() {
    if (!selectedSpotId) return;
    setSpots((items) => items.filter((spot) => spot.id !== selectedSpotId));
    setSelectedSpotId(null);
  }

  async function handleBaseImageChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLocalImageUrl(URL.createObjectURL(file));
    await onUploadBaseImage(file);
  }

  return (
    <section className="setup-grid">
      <div className="annotation-panel">
        <PanelHeading title="Imagem base e vagas" subtitle="Clique na imagem para marcar os pontos da vaga" />
        <div className="annotation-toolbar">
          <label className="file-button">
            <Upload size={17} />
            <span>Imagem base</span>
            <input type="file" accept="image/*" onChange={handleBaseImageChange} />
          </label>
          <button onClick={finishSpot} disabled={currentPolygon.length < 3}>
            <Check size={17} />
            <span>Fechar vaga</span>
          </button>
          <button onClick={() => setCurrentPolygon((polygon) => polygon.slice(0, -1))} disabled={!currentPolygon.length}>Desfazer ponto</button>
          <button onClick={() => setCurrentPolygon([])} disabled={!currentPolygon.length}>Limpar desenho</button>
          <button onClick={deleteSelected} disabled={!selectedSpotId}>Remover vaga</button>
          <button className="primary" onClick={() => onSaveSpots(spots)} disabled={!spots.length}>
            <Save size={17} />
            <span>Salvar vagas</span>
          </button>
        </div>
        {imageUrl ? (
          <canvas className="annotation-canvas" ref={canvasRef} onClick={handleCanvasClick} />
        ) : (
          <div className="empty-state">
            <MousePointer2 size={28} />
            <p>Envie uma imagem do estacionamento para começar a marcar as vagas.</p>
          </div>
        )}
      </div>

      <div className="status-panel">
        <PanelHeading title="Vagas configuradas" subtitle={`${spots.length} vagas`} />
        <div className="spot-list">
          {spots.map((spot) => (
            <button
              className={`config-spot-row ${spot.id === selectedSpotId ? 'selected' : ''}`}
              key={spot.id}
              onClick={() => setSelectedSpotId(spot.id)}
            >
              <span className="spot-id">{spot.id}</span>
              <span>{spot.polygon.length} pontos</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProcessView({ canProcess, isProcessing, onProcessImage }: {
  canProcess: boolean;
  isProcessing: boolean;
  onProcessImage: (file: File) => Promise<void>;
}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  }

  return (
    <section className="process-grid">
      <div className="image-panel">
        <PanelHeading title="Processar imagem" subtitle="Envie uma foto nova do mesmo enquadramento configurado" />
        <div className="upload-zone">
          <label className="file-button large">
            <Upload size={18} />
            <span>Selecionar foto</span>
            <input type="file" accept="image/*" onChange={handleFileChange} />
          </label>
          <button className="primary" disabled={!selectedFile || !canProcess || isProcessing} onClick={() => selectedFile && onProcessImage(selectedFile)}>
            {isProcessing ? 'Processando...' : 'Rodar YOLO'}
          </button>
        </div>
        {!canProcess && <Notice tone="error" message="Configure e salve as vagas antes de processar uma imagem." />}
        {previewUrl && <img className="parking-image" src={previewUrl} alt="Prévia da imagem enviada" />}
      </div>
    </section>
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

function PanelHeading({ title, subtitle, right }: { title: string; subtitle: string; right?: string }) {
  return (
    <div className="panel-heading">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {right && <span className="loading">{right}</span>}
    </div>
  );
}

function Notice({ tone, message }: { tone: 'error' | 'success'; message: string }) {
  return (
    <section className={`notice ${tone}`} role="alert">
      {tone === 'error' ? <AlertCircle size={18} /> : <Check size={18} />}
      <span>{message}</span>
    </section>
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

function drawAnnotationCanvas(
  canvas: HTMLCanvasElement,
  image: HTMLImageElement,
  spots: ParkingSpotConfig[],
  currentPolygon: Point[],
  selectedSpotId: string | null,
) {
  const context = canvas.getContext('2d');
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0);
  spots.forEach((spot) => drawPolygon(context, spot.polygon, spot.id, spot.id === selectedSpotId ? '#f5bd2f' : '#16a06a'));
  drawPolygon(context, currentPolygon, 'nova', '#e56b45');
}

function drawPolygon(context: CanvasRenderingContext2D, polygon: Point[], label: string, color: string) {
  if (!polygon.length) return;
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(polygon[0][0], polygon[0][1]);
  polygon.slice(1).forEach(([x, y]) => context.lineTo(x, y));
  if (polygon.length >= 3) context.closePath();
  context.stroke();
  polygon.forEach(([x, y]) => {
    context.beginPath();
    context.arc(x, y, 5, 0, Math.PI * 2);
    context.fill();
  });
  context.font = '18px Arial';
  context.lineWidth = 4;
  context.strokeStyle = '#000';
  context.strokeText(label, polygon[0][0], polygon[0][1] - 8);
  context.fillText(label, polygon[0][0], polygon[0][1] - 8);
}

function nextSpotId(spots: ParkingSpotConfig[]) {
  const highest = spots.reduce((max, spot) => {
    const match = spot.id.match(/(\d+)$/);
    return Math.max(max, match ? Number(match[1]) : 0);
  }, 0);
  return `A${highest + 1}`;
}

async function responseText(response: Response, fallback: string) {
  try {
    const body = await response.json();
    return body.detail ?? fallback;
  } catch {
    return fallback;
  }
}

function formatConfidence(value: number | null) {
  if (value === null || value === undefined) return '-';
  return `${(value * 100).toFixed(0)}%`;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

createRoot(document.getElementById('root')!).render(<App />);
