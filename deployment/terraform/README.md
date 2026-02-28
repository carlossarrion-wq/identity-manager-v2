# Terraform Infrastructure for Identity Manager

Este directorio contiene la infraestructura como código (IaC) para desplegar Identity Manager en AWS.

## 📁 Estructura

```
terraform/
├── modules/
│   └── rds/                    # Módulo de RDS PostgreSQL
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── environments/
    ├── dev/                    # Entorno de desarrollo
    ├── pre/                    # Entorno de preproducción
    └── pro/                    # Entorno de producción
```

## 🚀 Recursos Creados

### RDS PostgreSQL
- **Instancia RDS** con PostgreSQL 15.4
- **Security Group** para controlar acceso
- **DB Subnet Group** para alta disponibilidad
- **Secrets Manager** para almacenar credenciales
- **Enhanced Monitoring** (opcional)
- **Backups automáticos** configurables
- **Encriptación** en reposo

### Inicialización Automática
- Ejecución automática del esquema v2
- Carga de datos iniciales (seeds)
- Configuración de tablas y vistas

## 📋 Prerequisitos

1. **Terraform** >= 1.0
2. **AWS CLI** configurado
3. **PostgreSQL client** (psql) instalado
4. **jq** para procesamiento JSON
5. Credenciales AWS con permisos para:
   - RDS
   - VPC/Subnets
   - Secrets Manager
   - IAM (para roles de monitoring)

## 🔧 Uso

### 1. Configurar Variables

```bash
cd environments/dev
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores
```

**Variables requeridas:**
- `vpc_id` - ID de tu VPC
- `subnet_ids` - IDs de subnets (opcional, se auto-descubren)
- `allowed_cidr_blocks` - CIDRs permitidos para acceso

### 2. Inicializar Terraform

```bash
terraform init
```

### 3. Planificar Cambios

```bash
terraform plan
```

### 4. Aplicar Infraestructura

```bash
terraform apply
```

Esto creará:
1. RDS PostgreSQL instance
2. Security groups y networking
3. Secrets Manager con credenciales
4. Ejecutará automáticamente:
   - `identity_manager_schema_v2.sql`
   - `insert_permission_types_v2.sql`
   - `insert_applications_v2.sql`
   - `insert_models_v2.sql`
   - `insert_modules_v2.sql`

### 5. Obtener Información

```bash
# Ver outputs
terraform output

# Obtener endpoint de RDS
terraform output rds_endpoint

# Obtener nombre del secreto
terraform output secret_name
```

## 🔐 Acceso a la Base de Datos

### Opción 1: Usando AWS Secrets Manager

```bash
# Obtener credenciales
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw secret_name) \
  --query SecretString --output text | jq .

# Conectar directamente
SECRET=$(aws secretsmanager get-secret-value --secret-id $(terraform output -raw secret_name) --query SecretString --output text)
DB_HOST=$(echo $SECRET | jq -r .host)
DB_USER=$(echo $SECRET | jq -r .username)
DB_PASS=$(echo $SECRET | jq -r .password)
DB_NAME=$(echo $SECRET | jq -r .dbname)

PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

### Opción 2: Desde EC2/Lambda

Las funciones Lambda pueden acceder al secreto usando el ARN:

```python
import boto3
import json

secrets_client = boto3.client('secretsmanager')
secret_arn = 'arn:aws:secretsmanager:...'  # Del output

response = secrets_client.get_secret_value(SecretId=secret_arn)
credentials = json.loads(response['SecretString'])

# Usar credentials['host'], credentials['username'], etc.
```

## 🌍 Entornos

### Development (dev)
- Instancia: `db.t3.micro`
- Backups: 3 días
- Deletion protection: Deshabilitado
- Skip final snapshot: Sí
- Monitoring: Deshabilitado

### Preproduction (pre)
- Instancia: `db.t3.small`
- Backups: 7 días
- Deletion protection: Habilitado
- Skip final snapshot: No
- Monitoring: Habilitado (60s)

### Production (pro)
- Instancia: `db.t3.medium` o superior
- Backups: 30 días
- Deletion protection: Habilitado
- Skip final snapshot: No
- Monitoring: Habilitado (60s)
- Multi-AZ: Recomendado

## 🔄 Actualización del Esquema

Si necesitas actualizar el esquema después del despliegue inicial:

```bash
# Opción 1: Forzar re-ejecución del null_resource
terraform taint module.rds.null_resource.init_database
terraform apply

# Opción 2: Ejecutar manualmente
SECRET=$(aws secretsmanager get-secret-value --secret-id $(terraform output -raw secret_name) --query SecretString --output text)
DB_HOST=$(echo $SECRET | jq -r .host)
DB_USER=$(echo $SECRET | jq -r .username)
DB_PASS=$(echo $SECRET | jq -r .password)
DB_NAME=$(echo $SECRET | jq -r .dbname)

PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f ../../../database/schema/identity_manager_schema_v2.sql
```

## 🗑️ Destruir Infraestructura

```bash
# CUIDADO: Esto eliminará todos los recursos
terraform destroy
```

## 📝 Nomenclatura

### Base de Datos
- Formato: `identity_manager_<env>_rds`
- Ejemplos: `identity_manager_dev_rds`, `identity_manager_pro_rds`

### Tablas
- Formato: `identity-manager-<función>-tbl`
- Ejemplo: `identity-manager-models-tbl`

### Secrets Manager
- Formato: `<aplicacion>-<entorno>-<tipo>-<detalle>`
- Ejemplo: `identity-mgmt-dev-db-admin`
- Componentes:
  - **aplicacion**: `identity-mgmt`
  - **entorno**: `dev`, `pre`, `pro`
  - **tipo**: `db` (credenciales de base de datos)
  - **detalle**: `admin` (acceso administrador)

### Recursos AWS
- RDS: `identity-manager-<env>-rds`
- Security Group: `identity-manager-<env>-rds-sg`
- Secret: `identity-mgmt-<env>-db-admin`

## 🔍 Troubleshooting

### Error: No se puede conectar a RDS

1. Verificar security group:
```bash
aws ec2 describe-security-groups --group-ids $(terraform output -raw security_group_id)
```

2. Verificar que estás en la VPC correcta o tienes acceso

### Error: Timeout al ejecutar scripts SQL

1. Aumentar el sleep en `null_resource`:
```hcl
# En modules/rds/main.tf
sleep 60  # Aumentar de 30 a 60 segundos
```

2. Verificar que psql está instalado:
```bash
which psql
psql --version
```

### Error: Secrets Manager no encontrado

Esperar unos segundos y reintentar. El secreto se crea después de RDS.

## 📚 Referencias

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)

## 🤝 Contribuir

Para añadir nuevos entornos o modificar la configuración:

1. Copiar `environments/dev` a nuevo entorno
2. Ajustar variables según necesidades
3. Actualizar este README
