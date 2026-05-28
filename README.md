# ParkTwin

ParkTwin é um projeto pessoal de visão computacional e digital twin para monitorar a ocupação de vagas em estacionamentos.

O objetivo do MVP é carregar imagens de um estacionamento, usar vagas definidas por polígonos, associar veículos detectados a essas vagas e gerar um estado digital simples com vagas livres, ocupadas ou incertas.

## Estrutura inicial

- `src/detection`: detecção de veículos em imagens ou vídeos.
- `src/parking`: representação de vagas, polígonos e associação entre veículos e vagas.
- `src/twin`: estado digital do estacionamento.
- `src/api`: reservado para uma API futura.
- `src/dashboard`: reservado para visualização futura.
- `data/samples`: arquivos de entrada de exemplo.
- `data/outputs`: saídas geradas pelo projeto.
- `docs`: documentação auxiliar.
- `scripts`: scripts utilitários.
- `tests`: testes automatizados.

## Escopo atual

Esta etapa cria apenas a estrutura inicial do projeto. A detecção com YOLO e o dashboard ainda não foram implementados.
