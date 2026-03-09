# 📁 Estructura de Terraform - Identity Manager

## 🏗️ Arquitectura General

```
deployment/terraform/
├── modules/              # Módulos reutilizables (componentes)
│   ├── frontend/        # CloudFront + S3 para frontend
│   ├── lambda/          # Funciones Lambda
│   ├── rds/             # Base de datos PostgreSQL
│   ├── secrets/         # Secrets Manager
│   └── vpc/             # VPC y networking
│
├── environments/         # Configuraciones por entorno
│   ├── dev/             # Desarrollo
│   ├── pre/             # Pre-producción
│   └── pro/             # Producción
│
└── lambda-packages/      # Paquetes ZIP de Lambdas
```

---

## 📦 1. MÓDULOS (modules/)

Los módulos son **componentes reutilizables** que definen recursos de AWS. Se usan desde los entornos.

### 🔹 **modules/lambda/**

**Propósito**: Crear funciones Lambda con toda su configuración

**Recursos que crea**:
- ✅ Lambda Function
- ✅ IAM Role y Policies (Cognito, Secrets Manager, CloudWatch, VPC)
- ✅ CloudWatch Log Group
- ✅ Lambda Function URL (opcional)
- ✅ CloudWatch Alarms (opcional)

**Configuración incluida**:
```hcl
# Runtime y Layer
runtime = "python3.12"
layers = ["arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"]

# Permisos IAM automáticos
- CloudWatch Logs
- Secrets Manager (DB, JWT, Email)
- Cognito (AdminListGroupsForUser, etc.)
- VPC (si se configura)
```

**Archivos**:
- `main.tf`: Definición de recursos
- `variables.tf`: Variables de entrada
- `outputs.tf`: Valores de salida (ARNs, nombres, etc.)

---

### 🔹 **modules/rds/**

**Propósito**: Crear base de datos PostgreSQL en RDS

**Recursos que crea**:
- ✅ RDS PostgreSQL Instance
- ✅ DB Subnet Group
- ✅ Security Group
- ✅ Secret en Secrets Manager (credenciales)
- ✅ CloudWatch Alarms (opcional)

**Configuración**:
```hcl
# Base de datos
engine         = "postgres"
engine_version = "15.x"
instance_class = "db.t3.micro"

# Networking
publicly_accessible = true  # Para dev
subnet_ids         = [...]  # Subnets públicas

# Seguridad
master_username = "postgres"
master_password = (generado automáticamente)
```

---

### 🔹 **modules/secrets/**

**Propósito**: Crear secrets en AWS Secrets Manager

**Recursos que crea**:
- ✅ Secret para credenciales SMTP de email

**Uso**:
```hcl
module "secrets" {
  source = "../../modules/secrets"
  
  project_name = "identity-mgmt"
  environment  = "dev"
}
```

---

### 🔹 **modules/frontend/**

**Propósito**: Desplegar frontend estático en S3 + CloudFront

**Recursos que crea**:
- ✅ S3 Bucket (privado)
- ✅ CloudFront Distribution
- ✅ Origin Access Identity
- ✅ Bucket Policy

**Configuración**:
```hcl
# CloudFront
price_class = "PriceClass_100"  # Solo EU/US
default_root_object = "login.html"

# Cache
default_ttl = 3600
max_ttl     = 86400
```

---

### 🔹 **modules/vpc/**

**Propósito**: Crear VPC y networking (actualmente no usado, se usa VPC existente)

---

## 🌍 2. ENTORNOS (environments/)

Cada entorno tiene su propia configuración y usa los módulos.

### 📂 **environments/dev/**

Configuración del entorno de **desarrollo**.

#### **Archivos principales**:

##### **1. main.tf** - Configuración base y módulos principales

```hcl
# ¿Qué despliega?
├── Provider AWS (región, tags)
├── Data sources (VPC, Subnets existentes)
├── module "rds"           # Base de datos PostgreSQL
├── module "secrets"       # Secrets Manager (email SMTP)
├── JWT Secret             # Secret para tokens JWT
└── module "lambda"        # Lambda API (identity-mgmt-dev-api-lmbd)
```

**Recursos desplegados**:
1. **RDS PostgreSQL**
   - Nombre: `identity-manager-dev-rds`
   - Engine: PostgreSQL 15.x
   - Instance: db.t3.micro
   - Storage: 20 GB
   - Publicly accessible: true

2. **Secrets Manager**
   - `identity-mgmt-dev-db-admin` (credenciales DB)
   - `identity-mgmt-dev-key-access` (JWT secret)
   - `identity-mgmt-dev-email-smtp` (SMTP credentials)

3. **Lambda API**
   - Nombre: `identity-mgmt-dev-api-lmbd`
   - Runtime: Python 3.12
   - Layer: psycopg2-binary
   - Timeout: 30s
   - Memory: 512 MB

---

##### **2. auth-lambda.tf** - Lambda de autenticación

```hcl
# ¿Qué despliega?
└── module "auth_lambda"   # Lambda Auth (login-authorization-service)
```

**Recursos desplegados**:
1. **Lambda Auth**
   - Nombre: `login-authorization-service`
   - Runtime: Python 3.12
   - Layer: psycopg2-binary
   - Timeout: 30s
   - Memory: 512 MB
   - Permisos: Cognito, Secrets Manager, CloudWatch

---

##### **3. frontend.tf** - Frontend estático

```hcl
# ¿Qué despliega?
└── module "frontend"      # S3 + CloudFront
```

**Recursos desplegados**:
1. **S3 Bucket**
   - Nombre: `identity-mgmt-dev-frontend-<random>`
   - Privado (acceso solo via CloudFront)

2. **CloudFront Distribution**
   - URL: `https://dxxn3uthouo8.cloudfront.net`
   - Origin: S3 bucket
   - Cache: 1 hora default

---

##### **4. variables.tf** - Variables de entrada

Define todas las variables que se pueden configurar:

```hcl
# Variables principales
- aws_region              # eu-west-1
- db_master_username      # postgres
- db_instance_class       # db.t3.micro
- db_allocated_storage    # 20
- postgres_version        # 15.x
- db_publicly_accessible  # true
- db_backup_retention     # 7 días
- db_deletion_protection  # false (dev)
```

---

##### **5. terraform.tfvars** - Valores de variables

Archivo con los valores específicos del entorno:

```hcl
aws_region = "eu-west-1"

# Database
db_master_username      = "postgres"
db_instance_class       = "db.t3.micro"
db_allocated_storage    = 20
postgres_version        = "15.8"
db_publicly_accessible  = true
db_backup_retention_period = 7
db_deletion_protection  = false
db_skip_final_snapshot  = true
```

---

##### **6. outputs.tf** - Valores de salida

Define qué información se muestra después del deployment:

```hcl
# Outputs disponibles
- rds_endpoint              # Endpoint de la base de datos
- rds_secret_arn            # ARN del secret con credenciales
- lambda_function_name      # Nombre de Lambda API
- lambda_function_arn       # ARN de Lambda API
- auth_lambda_function_name # Nombre de Lambda Auth
- auth_lambda_function_arn  # ARN de Lambda Auth
- frontend_cloudfront_url   # URL de CloudFront
- frontend_s3_bucket        # Nombre del bucket S3
```

---

##### **7. README-AUTH-LAMBDA.md** - Documentación

Guía completa de deployment de la Lambda de autenticación.

---

##### **8. deploy-frontend.sh** - Script de deployment

Script para subir archivos del frontend a S3:

```bash
#!/bin/bash
# Sube archivos de frontend/ a S3
# Invalida cache de CloudFront
```

---

## 🎯 3. FLUJO DE DEPLOYMENT

### **Orden de creación de recursos**:

```
1. VPC (usa existente: vpc-04ba39cd0772a280b)
   └── Subnets públicas y privadas

2. Secrets Manager
   ├── identity-mgmt-dev-email-smtp
   └── identity-mgmt-dev-key-access (JWT)

3. RDS PostgreSQL
   ├── DB Instance
   ├── Security Group
   └── Secret: identity-mgmt-dev-db-admin

4. Lambda API (identity-mgmt-dev-api-lmbd)
   ├── IAM Role
   ├── Policies (Cognito, Secrets, CloudWatch)
   ├── CloudWatch Log Group
   └── Lambda Function

5. Lambda Auth (login-authorization-service)
   ├── IAM Role
   ├── Policies (Cognito, Secrets, CloudWatch)
   ├── CloudWatch Log Group
   └── Lambda Function

6. Frontend
   ├── S3 Bucket
   ├── CloudFront Distribution
   └── Origin Access Identity
```

---

## 📝 4. COMANDOS DE DEPLOYMENT

### **Deployment completo**:
```bash
cd deployment/terraform/environments/dev

# Inicializar (primera vez)
terraform init

# Ver plan
terraform plan

# Aplicar todo
terraform apply
```

### **Deployment selectivo**:

```bash
# Solo RDS
terraform apply -target=module.rds

# Solo Lambda API
terraform apply -target=module.lambda

# Solo Lambda Auth
terraform apply -target=module.auth_lambda

# Solo Frontend
terraform apply -target=module.frontend
```

### **Ver outputs**:
```bash
terraform output
terraform output rds_endpoint
terraform output lambda_function_name
```

### **Destruir recursos**:
```bash
# Destruir todo (¡CUIDADO!)
terraform destroy

# Destruir solo un módulo
terraform destroy -target=module.frontend
```

---

## 🔍 5. DÓNDE SE DEFINE CADA COSA

| Recurso | Módulo | Archivo de Entorno | Configuración |
|---------|--------|-------------------|---------------|
| **Lambda API** | `modules/lambda/` | `main.tf` | Runtime, Layer, Policies |
| **Lambda Auth** | `modules/lambda/` | `auth-lambda.tf` | Runtime, Layer, Policies |
| **RDS PostgreSQL** | `modules/rds/` | `main.tf` | Engine, Instance, Storage |
| **Secrets Manager** | `modules/secrets/` | `main.tf` | Email SMTP |
| **JWT Secret** | - | `main.tf` | Generado con random_password |
| **Frontend S3+CF** | `modules/frontend/` | `frontend.tf` | Bucket, Distribution |
| **IAM Policies** | `modules/lambda/` | `main.tf` | Cognito, Secrets, Logs |
| **CloudWatch Logs** | `modules/lambda/` | `main.tf` | Log Groups, Retention |

---

## 🎨 6. PERSONALIZACIÓN POR ENTORNO

Para crear un nuevo entorno (ej: `pre`):

```bash
# 1. Copiar estructura
cp -r environments/dev environments/pre

# 2. Modificar terraform.tfvars
# Cambiar valores específicos de pre

# 3. Modificar main.tf
# Cambiar nombres de recursos (dev -> pre)

# 4. Aplicar
cd environments/pre
terraform init
terraform apply
```

---

## 📚 7. ARCHIVOS DE ESTADO

```
terraform.tfstate         # Estado actual de la infraestructura
terraform.tfstate.backup  # Backup del estado anterior
```

**⚠️ IMPORTANTE**: 
- No commitear estos archivos a Git
- Usar S3 backend para producción
- Habilitar state locking con DynamoDB

---

## 🔐 8. SEGURIDAD

### **Secrets**:
- ✅ Credenciales DB en Secrets Manager
- ✅ JWT secret en Secrets Manager
- ✅ SMTP credentials en Secrets Manager
- ❌ No hardcodear secrets en código

### **IAM**:
- ✅ Principio de mínimo privilegio
- ✅ Policies específicas por recurso
- ✅ Roles separados por Lambda

### **Networking**:
- ✅ RDS en subnets públicas (solo dev)
- ✅ Security Groups restrictivos
- ⚠️ Producción: usar subnets privadas + VPC

---

## 📖 9. DOCUMENTACIÓN ADICIONAL

- `README.md` - Documentación general de Terraform
- `README-AUTH-LAMBDA.md` - Guía específica de Lambda Auth
- `modules/frontend/README.md` - Guía de deployment de frontend
- `modules/lambda/main.tf` - Comentarios inline de configuración

---

## 🎯 RESUMEN RÁPIDO

**¿Dónde está cada cosa?**

```
environments/dev/
├── main.tf              → RDS + Secrets + Lambda API
├── auth-lambda.tf       → Lambda Auth
├── frontend.tf          → S3 + CloudFront
├── variables.tf         → Definición de variables
├── terraform.tfvars     → Valores de variables
└── outputs.tf           → Outputs del deployment

modules/
├── lambda/              → Lógica de Lambdas (runtime, policies, logs)
├── rds/                 → Lógica de PostgreSQL
├── secrets/             → Lógica de Secrets Manager
└── frontend/            → Lógica de S3 + CloudFront
```

**¿Qué se despliega?**
1. ✅ PostgreSQL RDS (identity-manager-dev-rds)
2. ✅ 3 Secrets en Secrets Manager
3. ✅ Lambda API (identity-mgmt-dev-api-lmbd)
4. ✅ Lambda Auth (login-authorization-service)
5. ✅ Frontend S3 + CloudFront

**¿Cómo desplegar?**
```bash
cd deployment/terraform/environments/dev
terraform init
terraform apply