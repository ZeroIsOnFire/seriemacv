# NuExtract com Docker

[Voltar ao guia completo](index.md) · [English](../en/nuextract-docker.md)

Este serviço opcional executa NuExtract por um `llama-server` local; o seriemaCV não
o instala nem inicia. O endpoint fica em `127.0.0.1` e o modelo permanece em um
volume Docker dedicado.

## Iniciar

1. Instale Docker Desktop (Windows) ou Docker Engine (Linux).
2. Copie `docker/nuextract/.env.example` para `docker/nuextract/.env` e defina o
   nome do arquivo GGUF.
3. Coloque esse modelo no volume `seriemacv_nuextract_models`. Baixe modelos somente
   após revisar origem, licença e tamanho.
4. Execute:

```powershell
docker compose --env-file docker/nuextract/.env -f docker/nuextract/compose.yml up -d --build
curl http://127.0.0.1:8080/health
```

Configure o mesmo endpoint e modelo em `seriemacv.yml`. CPU é o padrão; camadas de
GPU exigem imagem/runtime llama.cpp compatível. Pare com
`docker compose -f docker/nuextract/compose.yml down`; remova o volume do modelo
somente se quiser apagar deliberadamente os downloads.
