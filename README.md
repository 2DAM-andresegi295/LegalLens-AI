# LegalLens AI

`LegalLens AI` es un SaaS de auditoría de contratos para despachos jurídicos. Permite registrar abogados, subir contratos en PDF, extraer texto, detectar cláusulas problemáticas y mostrar un informe con datos clave y banderas rojas.

## Qué incluye

- **Django** para login, panel privado, persistencia y administración.
- **FastAPI** como motor de análisis contractual.
- **POO** para modelar tipos de contrato y reglas de negocio.
- **Docker Compose** + **Nginx** para desplegar todo el stack.
- **Dataset** de pruebas con contratos legales y contratos trampa.

## Arquitectura

```text
Nginx (:80)
├── /        -> Django (:8000)
└── /api/    -> FastAPI (:8001)

db          -> PostgreSQL 16
backend     -> Django + Gunicorn
ai_engine   -> FastAPI + Uvicorn
```

## Estructura principal

```text
apps/
  web/      # proyecto Django
  api/      # proyecto FastAPI
backend/    # Dockerfile de Django
ai_engine/  # Dockerfile de FastAPI
nginx/      # reverse proxy
packages/   # dominio, agentes y lógica compartida
dataset/    # PDFs de prueba
tests/      # tests de API y agente
scripts/    # utilidades y smoke test
```

## Funcionalidades

- Registro e inicio de sesión de abogados.
- Subida de contratos por PDF.
- Auditoría automática de contratos de **alquiler** y **NDA**.
- Extracción de datos como nombres, DNI, fechas e importes.
- Detección de cláusulas abusivas o sospechosas.
- Visualización del informe en el panel privado.
- Admin de Django con métricas y análisis global.

## Flujo de uso

1. El usuario inicia sesión.
2. Sube un contrato PDF y elige el tipo de contrato.
3. Django envía el archivo o texto a FastAPI.
4. FastAPI analiza el contrato usando reglas POO y, opcionalmente, LLM.
5. Django guarda el resultado y lo muestra en el dashboard.

## Arranque rápido con Docker

```powershell
docker compose up --build
```

Servicios esperados:

- Web Django: `http://localhost/`
- Admin Django: `http://localhost/admin/`
- FastAPI: `http://localhost/api/health`
- Docs de FastAPI: `http://localhost/api/docs`

Para parar el stack:

```powershell
docker compose down
```

## Arranque local sin Docker

Instala dependencias:

```powershell
pip install -r requirements.txt
```

Lanza Django:

```powershell
python apps/web/manage.py migrate
python apps/web/manage.py runserver
```

Lanza FastAPI en otra terminal:

```powershell
uvicorn apps.api.app.main:app --reload --port 8001
```

## Variables de entorno

El proyecto usa las variables definidas en `.env.example`:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `LEGAL_ENGINE_BASE_URL`
- `LEGAL_ENGINE_TIMEOUT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `LEGAL_LLM_PROVIDER`
- `LEGAL_LLM_BASE_URL`
- `LEGAL_LLM_MODEL`
- `LEGAL_LLM_API_KEY`
- `LEGAL_LLM_TIMEOUT`

### Valores por defecto relevantes

Si no se definen credenciales de PostgreSQL, Django puede usar SQLite en local.

## Endpoints principales

### Django

- `GET /` — inicio / panel
- `GET|POST /accounts/signup/` — registro
- `GET|POST /contracts/new/` — subir contrato
- `GET /analyses/<id>/` — detalle del informe
- `GET /admin/` — administración
- `GET /health/` — healthcheck

### FastAPI

- `GET /api/health` — healthcheck
- `GET /api/` — información del motor
- `POST /api/v1/analyze` — analizar texto
- `POST /api/v1/analyze-file` — analizar PDF

## Ejemplo de petición

```json
{
  "title": "Contrato de alquiler",
  "text": "...",
  "contract_type": "rental",
  "source_type": "text"
}
```

## POO aplicada

- `packages/contracts.py` define `BaseContract`, `RentalContract`, `NDAContract` y `GeneralContract`.
- La lógica usa un enfoque tipo **Template Method** + **Factory**.
- Cada tipo de contrato concentra sus propias reglas de validación.
- `packages/entity_extraction.py` extrae entidades reutilizables.
- `packages/llm.py` añade soporte opcional para un LLM externo.

## Dataset de prueba

Incluido en `dataset/`:

- `contrato_alquiler_legal.pdf`
- `contrato_alquiler_trampa.pdf`
- `contrato_nda_legal.pdf`
- `contrato_nda_trampa.pdf`

## Tests y validación

Ejecutar tests:

```powershell
python -m unittest discover -s tests -v
python scripts/smoke_test.py
```

## Tecnologías

- Python 3
- Django 5
- FastAPI
- PostgreSQL
- Gunicorn
- Uvicorn
- Nginx
- pypdf
- httpx
- WhiteNoise
- Docker Compose

## Guion breve para demo

1. Ejecutar `docker compose up --build`.
2. Entrar en `http://localhost/`.
3. Registrarse o iniciar sesión.
4. Subir un PDF desde `dataset/`.
5. Mostrar el informe con banderas rojas.
6. Abrir `/admin/` para enseñar métricas globales.

## Estado de entrega

- Código fuente estructurado
- Docker Compose completo
- Proxy Nginx
- Dataset de prueba
- Tests básicos
- Variables de entorno documentadas

