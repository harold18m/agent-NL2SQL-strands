# 🚀 Despliegue del Agente NL2SQL en AWS Lambda

Este documento describe el proceso completo de despliegue del agente NL2SQL en AWS Lambda usando Terraform para infraestructura como código (IaC) y GitHub Actions para CI/CD.

## 📋 Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Prerrequisitos](#prerrequisitos)
- [Estructura de Archivos](#estructura-de-archivos)
- [Configuración Paso a Paso](#configuración-paso-a-paso)
- [Infraestructura con Terraform](#infraestructura-con-terraform)
- [CI/CD con GitHub Actions](#cicd-con-github-actions)
- [Variables de Entorno](#variables-de-entorno)
- [Comandos Útiles](#comandos-útiles)
- [Solución de Problemas](#solución-de-problemas)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AWS Cloud                                      │
│                                                                          │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   GitHub    │    │      ECR        │    │     Lambda Function     │  │
│  │   Actions   │───▶│  Docker Image   │───▶│    (Container Image)    │  │
│  │   (CI/CD)   │    │   nl2sql-agent  │    │      nl2sql-agent       │  │
│  └─────────────┘    └─────────────────┘    └───────────┬─────────────┘  │
│                                                         │                │
│                                            ┌────────────▼────────────┐  │
│                                            │    Function URL         │  │
│                                            │ (HTTP API Endpoint)     │  │
│                                            └────────────┬────────────┘  │
│                                                         │                │
└─────────────────────────────────────────────────────────┼────────────────┘
                                                          │
                                              ┌───────────▼───────────┐
                                              │   React Frontend /    │
                                              │   API Consumers       │
                                              └───────────────────────┘
```

### Componentes Principales

| Componente | Descripción |
|------------|-------------|
| **ECR (Elastic Container Registry)** | Almacena las imágenes Docker del agente |
| **Lambda Function** | Ejecuta el código del agente (FastAPI + Mangum) |
| **Function URL** | Endpoint HTTP público para acceder a la API |
| **IAM Role** | Permisos para Lambda (CloudWatch Logs, VPC, Secrets Manager) |
| **CloudWatch Logs** | Almacena logs de ejecución |
| **GitHub Actions** | Pipeline CI/CD automatizado |

---

## ✅ Prerrequisitos

### Herramientas Locales

```bash
# Instalar AWS CLI
brew install awscli

# Instalar Terraform
brew install terraform

# Instalar Docker Desktop
# Descargar desde: https://www.docker.com/products/docker-desktop/

# Verificar instalaciones
aws --version      # aws-cli/2.x.x
terraform --version # Terraform v1.x.x
docker --version   # Docker version 2x.x.x
```

### Configuración de AWS CLI

```bash
aws configure
# AWS Access Key ID: tu-access-key
# AWS Secret Access Key: tu-secret-key
# Default region: us-east-1
# Default output format: json

# Verificar configuración
aws sts get-caller-identity
```

---

## 📁 Estructura de Archivos

```
agent-NL2SQL-strands/
├── Dockerfile.lambda           # Dockerfile optimizado para Lambda
├── lambda_handler.py           # Handler Mangum para Lambda
├── .dockerignore               # Archivos excluidos del build Docker
│
├── terraform/                  # Infraestructura como código
│   ├── main.tf                 # Recursos AWS (ECR, Lambda, IAM, etc.)
│   ├── variables.tf            # Definición de variables
│   ├── outputs.tf              # Outputs del despliegue
│   ├── terraform.tfvars.example # Ejemplo de configuración
│   ├── terraform.tfvars        # Configuración real (NO commitear)
│   ├── terraform.tfstate       # Estado de Terraform (NO commitear)
│   └── .gitignore              # Exclusiones de Git para Terraform
│
├── .github/workflows/          # Pipelines CI/CD
│   ├── build-deploy-lambda.yml # Build y deploy de código
│   └── terraform.yml           # Gestión de infraestructura
│
└── scripts/
    └── aws-setup.sh            # Script alternativo de setup manual
```

---

## 🔧 Configuración Paso a Paso

### 1. Preparar el Lambda Handler

El archivo `lambda_handler.py` usa **Mangum** para adaptar FastAPI a AWS Lambda:

```python
"""AWS Lambda handler using Mangum to adapt FastAPI to Lambda (ASGI)."""
from mangum import Mangum
from app.api.routes import get_app

app = get_app()
handler = Mangum(app)
```

**¿Por qué Mangum?**
- FastAPI es un framework ASGI
- Lambda espera un handler síncrono
- Mangum actúa como adaptador entre ambos

### 2. Crear el Dockerfile

El `Dockerfile.lambda` usa **multi-stage build** para optimizar el tamaño:

```dockerfile
# Stage 1: Builder - Instala dependencias
FROM public.ecr.aws/lambda/python:3.11 AS builder
WORKDIR /var/task
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install --no-cache-dir .

# Stage 2: Runtime - Copia solo lo necesario
FROM public.ecr.aws/lambda/python:3.11
WORKDIR /var/task
COPY --from=builder /var/lang/lib/python3.11/site-packages /var/lang/lib/python3.11/site-packages
COPY app/ app/
COPY lambda_handler.py .
CMD ["lambda_handler.handler"]
```

**Beneficios del multi-stage build:**
- Imagen más pequeña (~500MB vs ~1.5GB)
- Cold starts más rápidos
- Sin archivos de desarrollo innecesarios

### 3. Configurar `.dockerignore`

Excluye archivos innecesarios del build:

```
.git/
.venv/
tests/
docs/
*.md
.env
__pycache__/
```

---

## 🏗️ Infraestructura con Terraform

### Recursos Creados

El archivo `terraform/main.tf` crea:

| Recurso | Nombre | Descripción |
|---------|--------|-------------|
| `aws_ecr_repository` | nl2sql-agent | Repositorio de imágenes Docker |
| `aws_ecr_lifecycle_policy` | - | Mantiene solo las últimas 10 imágenes |
| `aws_iam_role` | nl2sql-agent-lambda-role | Rol de ejecución para Lambda |
| `aws_lambda_function` | nl2sql-agent | Función Lambda (container image) |
| `aws_lambda_function_url` | - | URL HTTP pública |
| `aws_cloudwatch_log_group` | /aws/lambda/nl2sql-agent | Logs con retención 14 días |
| `aws_iam_user` | nl2sql-agent-github-actions | Usuario para CI/CD |

### Desplegar Infraestructura

```bash
cd terraform

# 1. Crear archivo de configuración
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores

# 2. Inicializar Terraform
terraform init

# 3. Ver plan de ejecución
terraform plan

# 4. Aplicar cambios
terraform apply
```

### Primer Despliegue (Imagen Inicial)

⚠️ **Importante**: Antes del primer `terraform apply`, debes subir una imagen inicial a ECR:

```bash
# 1. Crear solo el repositorio ECR primero
terraform apply -target=aws_ecr_repository.lambda

# 2. Login a ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# 3. Build de imagen (IMPORTANTE: usar --platform linux/amd64 en Mac M1/M2)
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -t $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/nl2sql-agent:latest \
  -f Dockerfile.lambda .

# 4. Push a ECR
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/nl2sql-agent:latest

# 5. Ahora sí, aplicar todo
terraform apply
```

### Outputs de Terraform

Después de `terraform apply`:

```bash
# Ver todos los outputs
terraform output

# Outputs importantes:
terraform output function_url                    # URL de la API
terraform output -raw github_actions_access_key_id      # Para GitHub Secrets
terraform output -raw github_actions_secret_access_key  # Para GitHub Secrets
```

---

## 🔄 CI/CD con GitHub Actions

### Workflow: Build & Deploy (`build-deploy-lambda.yml`)

Se ejecuta en cada push a `main`:

1. ✅ Checkout del código
2. ✅ Configura credenciales AWS
3. ✅ Login a ECR
4. ✅ Ejecuta tests con pytest
5. ✅ Build de imagen Docker
6. ✅ Push a ECR (con tag SHA y latest)
7. ✅ Actualiza Lambda function
8. ✅ Espera a que Lambda esté lista
9. ✅ Test de health check

### Workflow: Terraform (`terraform.yml`)

Gestiona la infraestructura:

- **Push a main** (cambios en `terraform/`): Aplica automáticamente
- **Pull Request**: Solo muestra el plan
- **Manual**: Permite `plan`, `apply` o `destroy`

### Configurar GitHub Secrets

En tu repositorio: **Settings → Secrets and variables → Actions**

| Secret | Valor | Obtener con |
|--------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | Access Key para CI/CD | `terraform output -raw github_actions_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | Secret Key para CI/CD | `terraform output -raw github_actions_secret_access_key` |
| `AWS_REGION` | `us-east-1` | - |
| `ECR_REPOSITORY` | `nl2sql-agent` | - |
| `LAMBDA_FUNCTION_NAME` | `nl2sql-agent` | - |

---

## 🔐 Variables de Entorno

### En Lambda (Producción)

Configura las variables de entorno de tu aplicación:

```bash
aws lambda update-function-configuration \
  --function-name nl2sql-agent \
  --environment 'Variables={
    DATABASE_URL=postgresql://user:pass@host:5432/db,
    GEMINI_API_KEY=tu-api-key,
    ENVIRONMENT=production,
    LOG_LEVEL=INFO
  }'
```

### Variables Disponibles

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://...` |
| `GEMINI_API_KEY` | API Key de Google Gemini | `AIzaSy...` |
| `ENVIRONMENT` | Entorno de ejecución | `production` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

---

## 🛠️ Comandos Útiles

### Verificar Despliegue

```bash
# Health check
curl https://tu-function-url.lambda-url.us-east-1.on.aws/health

# Hacer una pregunta
curl -X POST https://tu-function-url.lambda-url.us-east-1.on.aws/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuántos clientes hay?"}'
```

### Ver Logs

```bash
# Logs en tiempo real
aws logs tail /aws/lambda/nl2sql-agent --follow

# Últimos 10 minutos
aws logs tail /aws/lambda/nl2sql-agent --since 10m
```

### Actualizar Código Manualmente

```bash
# Build y push
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -t ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/nl2sql-agent:latest \
  -f Dockerfile.lambda .

docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/nl2sql-agent:latest

# Actualizar Lambda
aws lambda update-function-code \
  --function-name nl2sql-agent \
  --image-uri ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/nl2sql-agent:latest

# Esperar a que esté lista
aws lambda wait function-updated --function-name nl2sql-agent
```

### Destruir Infraestructura

```bash
cd terraform
terraform destroy
```

---

## 🔧 Solución de Problemas

### Error: "Source image does not exist"

**Causa**: No hay imagen en ECR antes de crear Lambda.

**Solución**: Subir imagen inicial antes de `terraform apply`:
```bash
terraform apply -target=aws_ecr_repository.lambda
# Luego build y push de imagen
# Finalmente terraform apply
```

### Error: "Image manifest type not supported"

**Causa**: Imagen construida con arquitectura ARM (Mac M1/M2) en lugar de x86_64.

**Solución**: Usar flags correctos en el build:
```bash
docker build --platform linux/amd64 --provenance=false --sbom=false ...
```

### Error: Timeout en Lambda

**Causa**: El timeout por defecto (3s) es muy corto para AI.

**Solución**: Aumentar timeout (ya configurado en 60s):
```hcl
# En terraform/variables.tf
variable "lambda_timeout" {
  default = 60  # segundos
}
```

### Error: Out of Memory

**Causa**: Memoria insuficiente para cargar modelos.

**Solución**: Aumentar memoria (ya configurado en 1024MB):
```hcl
# En terraform/variables.tf
variable "lambda_memory" {
  default = 1024  # MB
}
```

### Cold Starts Lentos

**Causas y soluciones**:
1. **Imagen grande**: Usar multi-stage build ✅
2. **Muchas dependencias**: Optimizar `pyproject.toml`
3. **Init pesado**: Usar lazy loading para conexiones

### Ver Errores Detallados

```bash
# Ver logs con errores
aws logs filter-log-events \
  --log-group-name /aws/lambda/nl2sql-agent \
  --filter-pattern "ERROR"
```

---

## 📊 Costos Estimados

| Servicio | Uso Gratuito (Free Tier) | Costo Adicional |
|----------|-------------------------|-----------------|
| Lambda | 1M requests/mes, 400K GB-s | $0.20/1M requests |
| ECR | 500MB storage | $0.10/GB/mes |
| CloudWatch Logs | 5GB ingestion | $0.50/GB |
| Data Transfer | 1GB/mes | $0.09/GB |

**Estimación para uso moderado (~10K requests/mes)**: ~$5-10/mes

---

## 📚 Referencias

- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [Mangum - ASGI Adapter for AWS Lambda](https://mangum.io/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions for AWS](https://github.com/aws-actions)

---

## 📝 Historial de Cambios

| Fecha | Cambio |
|-------|--------|
| 2025-11-25 | Despliegue inicial con Terraform y GitHub Actions |

---

**Creado por**: GitHub Copilot  
**Última actualización**: 25 de noviembre de 2025
