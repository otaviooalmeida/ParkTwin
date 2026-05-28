# ParkTwin

ParkTwin é um projeto de visão computacional e digital twin para monitorar a ocupação de vagas em estacionamentos a partir de imagens.

O pipeline atual carrega uma imagem, detecta veículos com YOLO, cruza as detecções com vagas anotadas manualmente e gera dois outputs:

- uma imagem anotada com cada vaga marcada como `free` ou `occupied`;
- um arquivo JSON com o estado digital do estacionamento.

## Exemplo Visual

Imagem base:

![Imagem base](data/samples/baseline.jpg)

Resultado anotado:

![Resultado anotado](data/outputs/baseline_annotated.jpg)


## Como Funciona

O ParkTwin usa uma imagem fixa de referência da câmera e um arquivo JSON com as vagas desenhadas como polígonos.

Fluxo:

```text
imagem -> YOLO -> VehicleDetection -> vagas anotadas -> ocupação -> twin state + imagem anotada
```

A ocupação é calculada pela área de sobreposição entre a bounding box do veículo e o polígono da vaga. Por padrão, se pelo menos `10%` da área da bbox do veículo estiver dentro da vaga, a vaga é marcada como `occupied`.

## Estrutura do Projeto

```text
.
├── data/
│   ├── samples/              # imagens e JSON de vagas
│   └── outputs/              # imagens anotadas e estados JSON
├── scripts/
│   ├── annotate_spots.py      # anotador com janela OpenCV
│   ├── annotate_spots_web.py  # anotador via navegador
│   ├── run_detection.py       # roda apenas a detecção YOLO
│   └── run_pipeline_image.py  # roda o pipeline completo
├── src/
│   ├── detection/             # detector YOLO
│   ├── parking/               # vagas, geometria, ocupação e visualização
│   └── twin/                  # estado digital do estacionamento
└── tests/                     # testes automatizados
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

Exemplo de saída:

```json
[
  {
    "bbox": [120.5, 80.2, 300.1, 220.8],
    "class_name": "car",
    "confidence": 0.87
  }
]
```

O detector filtra apenas:

- `car`
- `motorcycle`
- `bus`
- `truck`

## Twin State

O estado salvo em JSON tem este formato:

```json
{
  "timestamp": "2026-05-28T18:17:20.654879+00:00",
  "spots": [
    {
      "id": "A1",
      "polygon": [[993, 56], [1003, 17], [952, 12], [947, 49]],
      "status": "free",
      "confidence": null
    }
  ],
  "total_spots": 44,
  "occupied_count": 12,
  "free_count": 32,
  "uncertain_count": 0
}
```


