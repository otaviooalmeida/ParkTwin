# ParkTwin

[![CI](https://github.com/otaviooalmeida/ParkTwin/actions/workflows/ci.yml/badge.svg)](https://github.com/otaviooalmeida/ParkTwin/actions/workflows/ci.yml)

Sistema de monitoramento de vagas com visão computacional e digital twin. O ParkTwin detecta veículos com YOLO, associa cada detecção a uma vaga e mantém o estado do estacionamento em SQLite.

## Funcionalidades

- Classificação de vagas como `free`, `uncertain` ou `occupied`.
- Associação veículo–vaga 1:1 e confirmação temporal de mudanças.
- Processamento de imagens, streams JPEG e transmissões do YouTube.
- API FastAPI para configuração, processamento, histórico e eventos.
- Dashboard React/Vite para monitoramento, upload e anotação de vagas.
- Histórico paginado, retenção configurável e isolamento por estacionamento.

## Arquitetura

```text
imagem ou stream
      ↓
YOLO → associação com polígonos → estabilização temporal
      ↓
SQLite + imagem anotada
      ↓
FastAPI → React/Vite
```

```text
src/api/        API HTTP
src/detection/  integração com YOLO
src/parking/    geometria, ocupação e visualização
src/parktwin/   orquestração e avaliação
src/twin/       estado digital e persistência
frontend/       aplicação React/Vite
scripts/        anotação, processamento e workers
tests/          testes automatizados
```

## Requisitos

- Python 3.12
- Node.js 20.19+ ou 22.12+
- Docker e Docker Compose, para execução em containers
- Peso `yolo11s.pt` na raiz do projeto

Baixe o peso do modelo após instalar as dependências:

```bash
python -c "from ultralytics import YOLO; YOLO('yolo11s.pt')"
```

## Execução com Docker

```bash
cp .env.example .env
docker compose up --build api web
```

- Frontend: `http://localhost:8080`
- API: `http://localhost:8000`
- Documentação da API: `http://localhost:8000/docs`

Para iniciar também o worker do YouTube:

```bash
docker compose --profile worker up --build
```

Os dados persistentes ficam em `data/`.

## Execução local

Instale o backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Inicie a API:

```bash
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Inicie o frontend em outro terminal:

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Configuração das vagas

As vagas são polígonos vinculados ao enquadramento da câmera:

```json
[
  {
    "id": "A1",
    "polygon": [[993, 56], [1003, 17], [952, 12], [947, 49]]
  }
]
```

Elas podem ser desenhadas no frontend ou pelo anotador local:

```bash
python3 scripts/annotate_spots.py data/samples/baseline.jpg \
  --input data/samples/spots_annotated.json \
  --output data/samples/spots_annotated.json
```

## Processamento

Processar uma imagem e persistir o resultado:

```bash
python3 scripts/run_parktwin.py data/samples/baseline.jpg \
  --spots data/samples/spots_annotated.json \
  --model yolo11s.pt
```

Monitorar uma transmissão do YouTube:

```bash
python3 scripts/run_parktwin_youtube.py \
  --youtube-url "URL_DA_TRANSMISSAO" \
  --spots data/samples/spots_annotated.json \
  --model yolo11s.pt
```

As principais opções estão documentadas em `.env.example`, incluindo thresholds, quantidade de frames para confirmação e retenção de snapshots.

## Qualidade

Instale as dependências de desenvolvimento e execute os mesmos checks do CI:

```bash
pip install -r requirements-dev.txt
make check
```

O CI valida:

- formatação e lint com Ruff;
- testes, cobertura mínima de 75% e smoke test com YOLO real;
- auditoria e build do frontend;
- configuração do Docker Compose e builds completos das imagens.

## Avaliação

O avaliador gera acurácia, F1 macro, métricas por classe e matriz de confusão sobre imagens rotuladas:

```bash
cp evaluation/manifest.example.json evaluation/manifest.json
python3 scripts/evaluate_parktwin.py evaluation/manifest.json --model yolo11s.pt
```

Antes da execução, revise os rótulos do manifesto e marque os casos validados com `verified: true`.
