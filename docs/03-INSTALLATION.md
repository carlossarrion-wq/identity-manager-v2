# Guía de Instalación

## 📋 Requisitos Previos

### Software Requerido
- **AWS CLI** v2.x
- **Terraform** >= 1.0
- **Python** 3.12+
- **Go** 1.21+ (para proxy)
- **PostgreSQL Client** (psql)
- **Node.js** 18+ (para frontend)
- **Docker** (opcional)

### Acceso AWS
- Cuenta AWS activa
- Credenciales configuradas
- Permisos para:
  - Lambda
  - RDS
  - Cognito
  - VPC
  - Secrets Manager
  - SES (para emails)

## 🚀 Instalación Rápida

### 1. Clonar Repositorio

```bash
git clone https://github.com/carlossarrion-wq/identity-manager-v2.git
cd identity-manager-v2
```

### 2. Configurar AWS

```bash
aws configure
# Ingresar:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: eu-west-1
# - Default output format: json
```

### 3. Desplegar Infraestructura

```bash
cd deployment/terraform/environments/dev

# Copiar y editar variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Inicializar Terraform
terraform init

# Revisar plan
terraform plan

# Aplicar
terraform apply
```

### 4. Configurar Cognito

```bash
# Crear User Pool (manual en consola AWS o con Terraform)
# Anotar:
# - User Pool ID
# - Region

# Actualizar configuración en BD
psql -h <rds-endpoint> -U postgres -d identity_manager_dev_rds
```

```sql
UPDATE "identity-manager-config-tbl"
SET config_value = 'eu-west-1_UaMIbG9pD'
WHERE config_key = 'cognito_user_pool_id';
```

### 5. Desplegar Lambda

```bash
cd backend/lambdas/identity-mgmt-api

# Instalar dependencias
pip3 install -r requirements.txt -t .

# Empaquetar
zip -r lambda.zip .

# Desplegar
aws lambda update-function-code \
  --function-name identity-mgmt-dev-api-lmbd \
  --zip-file fileb://lambda.zip \
  --region eu-west-1
```

### 6. Desplegar Proxy Bedrock

```bash
cd proxy-bedrock

# Configurar variables
cp .env.example .env
nano .env

# Compilar
go build -o bin/proxy-bedrock ./cmd

# Ejecutar localmente (testing)
./bin/proxy-bedrock

# O desplegar en ECS (ver sección Docker)
```

### 7. Configurar Frontend

```bash
cd frontend/dashboard

# Editar configuración
nano js/config.js

# Actualizar API_BASE_URL con tu endpoint
```

## 🔧 Configuración Detallada

### Variables de Entorno - Lambda

Configurar en AWS Lambda Console o Terraform:

```bash
DB_SECRET_NAME=identity-mgmt-dev-db-admin
JWT_SECRET_NAME=identity-mgmt-dev-jwt-secret
COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD
COGNITO_REGION=eu-west-1
AWS_REGION=eu-west-1
```

### Variables de Entorno - Proxy

Archivo `.env`:

```bash
# AWS Bedrock
AWS_BEDROCK_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_BEDROCK_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_BEDROCK_REGION=eu-west-1
AWS_BEDROCK_ANTHROPIC_DEFAULT_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0

# PostgreSQL
DB_HOST=identity-manager-dev-rds.xxxxx.eu-west-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=identity_manager_dev_rds
DB_USER=postgres
DB_PASSWORD=<from-secrets-manager>
DB_SSLMODE=require
DB_MAX_CONNS=25
DB_MIN_CONNS=5

# JWT
JWT_SECRET_KEY=<from-secrets-manager>
JWT_ISSUER=bedrock-proxy
JWT_AUDIENCE=bedrock-api

# Server
PORT=8081
LOG_LEVEL=info
```

### Terraform Variables

Archivo `terraform.tfvars`:

```hcl
# VPC Configuration
vpc_id = "vpc-xxxxx"
subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]

# RDS Configuration
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
db_name = "identity_manager_dev_rds"
db_username = "postgres"

# Security
allowed_cidr_blocks = ["10.0.0.0/16"]

# Backup
backup_retention_period = 7
skip_final_snapshot = false

# Tags
environment = "dev"
project = "identity-manager"
```

## 🐳 Despliegue con Docker

### Proxy Bedrock

```bash
cd proxy-bedrock

# Build
docker build -t bedrock-proxy:latest .

# Run localmente
docker run -p 8081:8081 --env-file .env bedrock-proxy:latest

# Push a ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin \
  701055077130.dkr.ecr.eu-west-1.amazonaws.com

docker tag bedrock-proxy:latest \
  701055077130.dkr.ecr.eu-west-1.amazonaws.com/bedrock-proxy:latest

docker push \
  701055077130.dkr.ecr.eu-west-1.amazonaws.com/bedrock-proxy:latest

# Deploy en ECS
aws ecs update-service \
  --cluster bedrock-proxy-dev-cluster \
  --service bedrock-proxy-dev-service \
  --force-new-deployment \
  --region eu-west-1
```

## 📊 Verificación

### 1. Verificar RDS

```bash
# Obtener endpoint
terraform output rds_endpoint

# Conectar
psql -h <endpoint> -U postgres -d identity_manager_dev_rds

# Verificar tablas
\dt
```

### 2. Verificar Lambda

```bash
# Test
aws lambda invoke \
  --function-name identity-mgmt-dev-api-lmbd \
  --payload '{"operation":"get_config"}' \
  --region eu-west-1 \
  response.json

cat response.json
```

### 3. Verificar Proxy

```bash
# Health check
curl http://localhost:8081/health

# Test con token
curl -X POST http://localhost:8081/v1/messages \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 4. Verificar Frontend

```bash
# Abrir en navegador
open frontend/dashboard/index.html

# O servir con servidor local
cd frontend/dashboard
python3 -m http.server 8000
open http://localhost:8000
```

## 🔍 Troubleshooting

### Error: No se puede conectar a RDS

**Solución:**
```bash
# Verificar security group
aws ec2 describe-security-groups \
  --group-ids $(terraform output -raw security_group_id)

# Verificar que tu IP está permitida
# Agregar regla si es necesario
```

### Error: Lambda timeout

**Solución:**
```bash
# Aumentar timeout
aws lambda update-function-configuration \
  --function-name identity-mgmt-dev-api-lmbd \
  --timeout 300 \
  --region eu-west-1
```

### Error: Proxy no puede conectar a BD

**Solución:**
```bash
# Verificar variables de entorno
cat .env

# Verificar conectividad
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Verificar security group permite conexión desde proxy
```

### Error: Frontend no puede llamar API

**Solución:**
```javascript
// Verificar CORS en API Gateway
// Verificar API_BASE_URL en config.js
// Verificar que Lambda está desplegada
```

## 📝 Checklist Post-Instalación

- [ ] RDS desplegado y accesible
- [ ] Tablas creadas y seeds cargados
- [ ] Cognito User Pool configurado
- [ ] Lambda desplegada y funcionando
- [ ] Proxy desplegado y funcionando
- [ ] Frontend accesible
- [ ] Secrets Manager configurado
- [ ] Variables de entorno correctas
- [ ] Health checks pasando
- [ ] Logs visibles en CloudWatch
- [ ] Primer usuario creado
- [ ] Primer token generado
- [ ] Test end-to-end exitoso

## 🎯 Próximos Pasos

1. Crear primer usuario administrador
2. Asignar permisos
3. Generar token JWT
4. Configurar aplicaciones
5. Configurar módulos
6. Configurar perfiles de inferencia
7. Probar flujo completo

## 📚 Referencias

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda Deployment](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)