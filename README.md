# ParkTwin

[![CI](https://github.com/otaviooalmeida/ParkTwin/actions/workflows/ci.yml/badge.svg)](https://github.com/otaviooalmeida/ParkTwin/actions/workflows/ci.yml)

ParkTwin é um projeto de visão computacional e digital twin para monitorar a ocupação de vagas em estacionamentos a partir de imagens.

O pipeline atual carrega uma imagem, detecta veículos com YOLO, cruza as detecções com vagas anotadas manualmente e gera dois outputs:

- uma imagem anotada com cada vaga marcada como `free`, `uncertain` ou `occupied`;
- um arquivo JSON com o estado digital do estacionamento.

O ParkTwin mantém uma representação digital persistente do estacionamento. A cada nova imagem processada, o sistema atualiza o estado de cada vaga, registra eventos de mudança, calcula a taxa de ocupação e disponibiliza essas informações em um dashboard de monitoramento.

## Como Funciona

O ParkTwin usa uma imagem fixa de referência da câmera e um arquivo JSON com as vagas desenhadas como polígonos.

Fluxo:

```text
imagem -> YOLO -> VehicleDetection -> vagas anotadas -> ocupação -> twin state + imagem anotada
```

A ocupação é calculada pela área de sobreposição entre a bounding box do veículo e o polígono da vaga. A associação é 1:1: uma detecção não pode ocupar mais de uma vaga. Por padrão, sobreposições a partir de `10%` são `occupied`, entre `5%` e `10%` são `uncertain`, e mudanças precisam aparecer em dois frames consecutivos para serem confirmadas.

## Exemplo visual

Tela principal do dashboard, com a última imagem analisada e metadados:

<img width="780" height="480" alt="Screenshot from 2026-05-28 18-39-29" src="https://github.com/user-attachments/assets/95491f32-8186-4a12-98ca-22272f0a1b87" />

Histórico de ocupação:

<img width="780" height="480" alt="Screenshot from 2026-05-28 18-40-09" src="https://github.com/user-attachments/assets/c3246ac8-2f2b-49f8-98fe-ec8e0aee625a" />

## Estrutura do Projeto

```text
.
├── data/
│   ├── samples/              # imagens e JSON de vagas
│   └── outputs/              # imagens anotadas e estados JSON
├── scripts/
│   ├── annotate_spots.py      # anotador com janela OpenCV
│   ├── run_detection.py       # roda apenas a detecção YOLO
│   ├── run_parktwin.py        # gerenciamento do streamlit/sqlite
│   └── run_pipeline_image.py  # roda o pipeline completo
├── src/
│   ├── api/                   # API FastAPI para o produto web
│   ├── dashboard/             # dashboard Streamlit legado
│   ├── detection/             # detector YOLO
│   ├── parking/               # vagas, geometria, ocupação e visualização
│   ├── parktwin/               # orquestração central do pipeline
│   └── twin/                  # estado digital do estacionamento
```

## Instalação

Pré-requisitos: Python 3.12 e Node.js 20.19+ ou 22.12+. Docker é opcional para execução em containers.

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências de execução:

```bash
pip install -r requirements.txt
```

Para desenvolvimento, use o ambiente editável com testes, cobertura e lint:

```bash
pip install -r requirements-dev.txt
make check
```

Baixe uma vez o peso recomendado do YOLO:

```bash
python -c "from ultralytics import YOLO; YOLO('yolo11s.pt')"
```

O pipeline usa `yolo11s.pt` com `imgsz=1280` por padrão. Os pesos não são versionados no Git.

## Anotar Vagas para o seu estacionamento

As vagas precisam ser anotadas manualmente uma vez para uma câmera, resolução e enquadramento específicos.

Formato do JSON:

```json
[
  {
    "id": "A1",
    "polygon": [[993, 56], [1003, 17], [952, 12], [947, 49]]
  },
  {
    "id": "A2",
    "polygon": [[1006, 35], [1002, 72], [1055, 91], [1057, 42]]
  }
]
```

### Anotador OpenCV

Caso seu sistema seja simples e não precise de softwares específicos para anotação, é possível anotar usando o script a seguir:

```bash
python3 scripts/annotate_spots.py data/samples/baseline.jpg \
  --input data/samples/spots_annotated.json \
  --output data/samples/spots_annotated.json
```

## Rodar o Pipeline Completo

Para uma imagem:

```bash
python3 scripts/run_pipeline_image.py data/samples/baseline.jpg \
  --spots data/samples/spots_annotated.json \
  --model yolo11s.pt
```

Isso gera:

```text
data/outputs/baseline_state.json
data/outputs/baseline_annotated.jpg
```

Para todas as imagens `.jpg` em `data/samples`:

```bash
for img in data/samples/*.jpg; do
  python3 scripts/run_pipeline_image.py "$img" \
    --spots data/samples/spots_annotated.json \
    --model yolo11s.pt
done
```

## Twin State

O estado é salvo em JSON.

Além do JSON, o projeto também pode persistir snapshots em SQLite usando `scripts/run_parktwin.py`. Esse fluxo mantém histórico de ocupação, registra eventos somente quando o estado de uma vaga muda e preserva campos temporais como `occupied_since` e `last_changed_at`.

```bash
python3 scripts/run_parktwin.py data/samples/baseline.jpg \
  --spots data/samples/spots_annotated.json \
  --model yolo11s.pt
```

Isso salva:

```text
data/parktwin.db
data/outputs/latest_annotated.jpg
```

## Dashboard

O dashboard Streamlit fica em:

```text
src/dashboard/app.py
```

Para rodar:

```bash
streamlit run src/dashboard/app.py
```

Ele mostra:

- métricas gerais de ocupação;
- imagem anotada mais recente;
- histórico de ocupação;
- últimos eventos por vaga;
- tabela com o estado atual de cada vaga.

O dashboard lê os dados do SQLite em `data/parktwin.db`. Caso o banco ainda não exista ou esteja vazio, ele usa os arquivos `*_state.json` e `*_annotated.jpg` em `data/outputs/` como fallback.

## Produto Web com FastAPI e Node/React

A superfície de produto fica separada em dois serviços:

```text
worker Python ou upload manual -> data/parktwin.db + data/outputs/latest_annotated.jpg
FastAPI                        -> configuração, processamento, snapshots e imagem
React/Vite                     -> dashboard, anotação de vagas e upload de imagens
```

Fluxos disponíveis no frontend:

- `Monitorar`: visualiza a última imagem processada, métricas, histórico e eventos.
- `Configurar`: envia uma imagem base do estacionamento e desenha os polígonos das vagas no navegador.
- `Processar`: envia uma nova foto do mesmo enquadramento e roda YOLO usando as vagas salvas.

Endpoints principais:

```text
GET  /health
GET  /api/config
POST /api/config/base-image
GET  /api/config/base-image
GET  /api/config/spots
PUT  /api/config/spots
POST /api/process-image
GET  /api/snapshots/latest
GET  /api/history?limit=500&offset=0
GET  /api/events?limit=100&offset=0
GET  /api/images/latest
```

Para rodar a API localmente:

```bash
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Para rodar o frontend localmente:

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Variáveis de ambiente usadas pela API, Streamlit e workers:

```text
PARKTWIN_DB_PATH=data/parktwin.db
PARKTWIN_OUTPUTS_DIR=data/outputs
PARKTWIN_UPLOADS_DIR=data/uploads
PARKTWIN_BASE_IMAGE_PATH=data/uploads/base_image.jpg
PARKTWIN_SPOTS_PATH=data/samples/spots_annotated.json
PARKTWIN_MODEL_PATH=yolo11s.pt
PARKTWIN_CORS_ORIGINS=http://localhost:5173,http://localhost:8080
PARKTWIN_MAX_UPLOAD_BYTES=15728640
PARKTWIN_OCCUPANCY_THRESHOLD=0.10
PARKTWIN_UNCERTAIN_OVERLAP_THRESHOLD=0.05
PARKTWIN_CHANGE_CONFIRMATION_FRAMES=2
PARKTWIN_RETENTION_SNAPSHOTS=10000
PARKTWIN_LOG_LEVEL=INFO
```

### Deploy com Docker Compose

Subir API e frontend:

```bash
docker compose up --build api web
```

A API fica em `http://localhost:8000` e o frontend em `http://localhost:8080`.

Para ativar o worker contínuo de YouTube Live junto do produto:

```bash
cp .env.example .env
docker compose --profile worker up --build
```

O Compose monta `./data` como volume persistente e `./yolo11s.pt` em `/app/models/yolo11s.pt`. Confirme que o peso foi baixado antes de subir os serviços; ele fica fora do Git por ser um artefato grande.

## Monitoramento em tempo real pelo YouTube Live

Para monitorar a live `https://www.youtube.com/watch?v=EPKWu223XEg`, primeiro capture um frame base. Use esse frame para anotar as vagas; depois rode o monitor com o mesmo seletor de formato para manter a resolução igual.

```bash
python3 scripts/capture_youtube_frame.py \
  --youtube-url https://www.youtube.com/watch?v=EPKWu223XEg \
  --output data/samples/youtube_live_base.jpg
```

Anote esse frame:

```bash
python3 scripts/annotate_spots_web.py data/samples/youtube_live_base.jpg \
  --input data/samples/spots_youtube_live.json \
  --output data/samples/spots_youtube_live.json
```

Depois rode o monitoramento. O padrão processa 1 frame a cada 5 segundos, que é um limite conservador para deploy inicial com YOLO e evita gravar snapshots demais no SQLite.

```bash
python3 scripts/run_parktwin_youtube.py \
  --youtube-url https://www.youtube.com/watch?v=EPKWu223XEg \
  --spots data/samples/spots_youtube_live.json \
  --model yolo11s.pt \
  --interval 5
```

Esse processo atualiza continuamente:

```text
data/parktwin.db
data/outputs/latest_frame.jpg
data/outputs/latest_annotated.jpg
```

Em outro terminal, rode o dashboard:

```bash
streamlit run src/dashboard/app.py
```

No menu lateral, ative `Atualizar em tempo real` para o Streamlit recarregar os dados e a imagem anotada mais recente.

Para testar sem deixar o processo rodando indefinidamente:

```bash
python3 scripts/run_parktwin_youtube.py \
  --youtube-url https://www.youtube.com/watch?v=EPKWu223XEg \
  --spots data/samples/spots_youtube_live.json \
  --max-frames 10
```

O fluxo por JPEG direto continua disponível em `scripts/run_parktwin_stream.py` para câmeras que publicam snapshots `.jpg`.

## Avaliação e qualidade

O diretório `evaluation/` contém um manifesto de exemplo para montar um conjunto de validação versionável. Os rótulos precisam ser conferidos manualmente; uma saída gerada pelo próprio modelo não deve ser usada como verdade de referência.

```bash
cp evaluation/manifest.example.json evaluation/manifest.json
# revise os status esperados e marque os casos validados com `verified: true`
python3 scripts/evaluate_parktwin.py evaluation/manifest.json --model yolo11s.pt
```

O relatório inclui acurácia, F1 macro, métricas por classe e matriz de confusão. Para executar a mesma validação automatizada do CI:

```bash
make check
docker compose config --quiet
docker build --check .
docker build --check frontend
```
