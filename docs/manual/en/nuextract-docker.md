# NuExtract with Docker

[Back to the complete guide](index.md) · [Português](../pt-BR/nuextract-docker.md)

This optional service runs NuExtract through local `llama-server`; it is not
installed or started by seriemaCV. The endpoint is bound to `127.0.0.1` and the
model stays in a dedicated Docker volume.

## Start

1. Install Docker Desktop (Windows) or Docker Engine (Linux).
2. Copy `docker/nuextract/.env.example` to `docker/nuextract/.env`.
3. With no `NUEXTRACT_GGUF_PATH`, Compose downloads the official NuExtract3 Q4_K_M
   GGUF into `seriemacv_nuextract_models` on first start. To use a local GGUF,
   place it in `docker/nuextract/models/` and set its container path, for example
   `NUEXTRACT_GGUF_PATH=/external/my-model.gguf`.
4. Run:

```powershell
docker compose --env-file docker/nuextract/.env -f docker/nuextract/compose.yml up -d --build
curl http://127.0.0.1:8080/health
```

Configure the same endpoint and model in `seriemacv.yml`. CPU is the default;
GPU layers require a compatible GPU-enabled llama.cpp image/runtime. Stop with
`docker compose -f docker/nuextract/compose.yml down`; remove the model volume only
when you intentionally want to delete downloaded models.
