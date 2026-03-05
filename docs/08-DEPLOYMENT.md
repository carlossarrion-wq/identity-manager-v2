# Deployment y Operaciones

## 📋 Visión General

Guía para desplegar y operar Identity Manager v2 en diferentes ambientes.

## 🌍 Ambientes

### Development (dev)
- **Propósito**: Desarrollo y pruebas
- **RDS**: db.t3.micro
- **Lambda**: 512 MB
- **Backups**: 3 días
- **Deletion Protection**: No

### Preproduction (pre)
- **Propósito**: Testing y validación
- **RDS**: db.t3.small
- **Lambda**: 512 MB
- **Backups**: 7 días
- **Deletion Protection**: Sí

### Production (pro)
- **Propósito**: Producción
- **RDS**: db.t3.medium+
- **Lambda**: 1024 MB
- **Backups**: 30 días
- **Deletion Protection**: Sí
- **Multi-AZ**: Recomendado

## 🚀 Proceso de Deployment

### 1. Infraestructura (Terraform)

```bash
cd deployment/terraform/environments/<env>

# Inicializar
terraform init

# Planificar
terraform plan -out=tfplan

# Aplicar
terraform apply tfplan
```

### 2. Backend (Lambda)

```bash
cd backend/lambdas/identity-mgmt-api

# Instalar dependencias
pip3 install -r requirements.txt -t .

# Empaquetar
zip -r lambda.zip . -x "*.pyc" -x "__pycache__/*"

# Desplegar
aws lambda update-function-code \
  --function-name identity-mgmt-<env>-api-lmbd \
  --zip-file fileb://lambda.zip \
  --region eu-west-1
```

### 3. Proxy Bedrock (ECS)

```bash
cd proxy-bedrock

# Build imagen
docker build -t bedrock-proxy:latest .

# Tag para ECR
docker tag bedrock-proxy:latest \
  <account-id>.dkr.ecr.eu-west-1.amazonaws.com/bedrock-proxy:latest

# Push a ECR
docker push \
  <account-id>.dkr.ecr.eu-west-1.amazonaws.com/bedrock-proxy:latest

# Deploy en ECS
aws ecs update-service \
  --cluster bedrock-proxy-<env>-cluster \
  --service bedrock-proxy-<env>-service \
  --force-new-deployment \
  --region eu-west-1
```

### 4. Frontend

```bash
cd frontend/dashboard

# Configurar API endpoint
nano js/config.js

# Desplegar a S3 + CloudFront (si aplica)
aws s3 sync . s3://identity-manager-<env>-frontend/
aws cloudfront create-invalidation \
  --distribution-id <dist-id> \
  --paths "/*"
```

## 🔄 CI/CD Pipeline

### GitHub Actions (Ejemplo)

```yaml
name: Deploy to Dev

on:
  push:
    branches: [develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-1
      
      - name: Deploy Lambda
        run: |
          cd backend/lambdas/identity-mgmt-api
          pip3 install -r requirements.txt -t .
          zip -r lambda.zip .
          aws lambda update-function-code \
            --function-name identity-mgmt-dev-api-lmbd \
            --zip-file fileb://lambda.zip
```

## 📊 Monitoreo

### CloudWatch Dashboards

**Métricas Lambda:**
- Invocations
- Duration
- Errors
- Throttles
- Concurrent Executions

**Métricas RDS:**
- CPU Utilization
- Database Connections
- Read/Write IOPS
- Free Storage Space

**Métricas Proxy:**
- Request Count
- Response Time
- Error Rate
- Quota Usage

### Alarmas

```bash
# Ejemplo: Alarma de errores Lambda
aws cloudwatch put-metric-alarm \
  --alarm-name identity-mgmt-lambda-errors \
  --alarm-description "Lambda errors > 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

## 🔍 Logging

### CloudWatch Logs

**Lambda:**
- Log Group: `/aws/lambda/identity-mgmt-<env>-api-lmbd`
- Retention: 7-30 días

**Proxy:**
- Log Group: `/ecs/bedrock-proxy-<env>`
- Retention: 7-30 días
- Formato: JSON estructurado

### Queries Útiles

```sql
-- Errores en Lambda
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

-- Requests lentos en Proxy
fields @timestamp, duration_ms, user_id
| filter duration_ms > 5000
| sort duration_ms desc
| limit 50
```

## 🔐 Secrets Management

### AWS Secrets Manager

**Secrets requeridos:**
- `identity-mgmt-<env>-db-admin`: Credenciales RDS
- `identity-mgmt-<env>-jwt-secret`: Secret para JWT
- `identity-mgmt-<env>-email-smtp`: Credenciales SMTP

### Rotación

```bash
# Rotar secret de BD
aws secretsmanager rotate-secret \
  --secret-id identity-mgmt-<env>-db-admin \
  --rotation-lambda-arn <lambda-arn>
```

## 🔄 Rollback

### Lambda

```bash
# Listar versiones
aws lambda list-versions-by-function \
  --function-name identity-mgmt-<env>-api-lmbd

# Rollback a versión anterior
aws lambda update-alias \
  --function-name identity-mgmt-<env>-api-lmbd \
  --name PROD \
  --function-version <version-number>
```

### ECS

```bash
# Rollback a task definition anterior
aws ecs update-service \
  --cluster bedrock-proxy-<env>-cluster \
  --service bedrock-proxy-<env>-service \
  --task-definition bedrock-proxy:<revision>
```

## 📝 Checklist de Deployment

### Pre-Deployment
- [ ] Backup de base de datos
- [ ] Verificar secrets actualizados
- [ ] Tests pasando
- [ ] Code review aprobado
- [ ] Changelog actualizado

### Deployment
- [ ] Terraform apply exitoso
- [ ] Lambda desplegada
- [ ] Proxy desplegado
- [ ] Frontend desplegado
- [ ] Health checks pasando

### Post-Deployment
- [ ] Verificar logs sin errores
- [ ] Smoke tests exitosos
- [ ] Métricas normales
- [ ] Notificar al equipo
- [ ] Actualizar documentación

## 🆘 Troubleshooting

### Lambda no responde
1. Verificar CloudWatch Logs
2. Verificar timeout configuration
3. Verificar memory allocation
4. Verificar VPC/Security Groups

### RDS no accesible
1. Verificar Security Groups
2. Verificar subnet groups
3. Verificar credenciales
4. Verificar connection pool

### Proxy retorna 429
1. Verificar cuotas en BD
2. Verificar scheduler funcionando
3. Verificar límites configurados
4. Revisar logs de quota middleware

## 🔗 Referencias

- [Arquitectura del Sistema](./02-ARCHITECTURE.md)
- [Guía de Instalación](./03-INSTALLATION.md)
- [Base de Datos](./07-DATABASE.md)