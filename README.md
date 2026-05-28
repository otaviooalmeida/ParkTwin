# ParkTwin

ParkTwin é um projeto de visão computacional e digital twin para monitorar a ocupação de vagas em estacionamentos a partir de imagens.

O pipeline atual carrega uma imagem, detecta veículos com YOLO, cruza as detecções com vagas anotadas manualmente e gera dois outputs:

- uma imagem anotada com cada vaga marcada como `free` ou `occupied`;
- um arquivo JSON com o estado digital do estacionamento.

O ParkTwin mantém uma representação digital persistente do estacionamento. A cada nova imagem processada, o sistema atualiza o estado de cada vaga, registra eventos de mudança, calcula a taxa de ocupação e disponibiliza essas informações em um dashboard de monitoramento.


## Como Funciona

O ParkTwin usa uma imagem fixa de referência da câmera e um arquivo JSON com as vagas desenhadas como polígonos.

Fluxo:

```text
imagem -> YOLO -> VehicleDetection -> vagas anotadas -> ocupação -> twin state + imagem anotada
```

A ocupação é calculada pela área de sobreposição entre a bounding box do veículo e o polígono da vaga. Por padrão, se pelo menos `10%` da área da bbox do veículo estiver dentro da vaga, a vaga é marcada como `occupied`.

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
│   ├── dashboard/             # dashboard para visualização
│   ├── detection/             # detector YOLO
│   ├── parking/               # vagas, geometria, ocupação e visualização
│   └── twin/                  # estado digital do estacionamento
```

## Instalação

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

O projeto usa `yolo11s.pt` como modelo recomendado para este estacionamento, com `imgsz=1280` no pipeline.

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

Além do JSON, o projeto também pode persistir snapshots em SQLite usando `scripts/run_parktwin.py`. Esse fluxo mantém histórico de ocupação, eventos por vaga e campos temporais como `occupied_since` e `last_changed_at`.

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
