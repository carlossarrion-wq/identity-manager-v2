# Identity Manager v2

Sistema de gestión de identidades y permisos para usuarios de AWS Cognito con integración a AWS Bedrock.

## 📁 Estructura del Proyecto

```
identity-manager-v2/
├── database/                      # Base de datos
│   ├── schema/                    # Esquemas DDL
│   │   ├── identity_manager_schema_v2.sql (recomendado)
│   │   └── identity_manager_schema.sql (legacy)
│   ├── migrations/                # Migraciones de BD
│   └── seeds/                     # Datos iniciales
│       ├── insert_permission_types_v2.sql
│       ├── insert_applications_v2.sql
│       ├── insert_models_v2.sql
│       └── insert_modules_v2.sql
│
├── backend/                       # Backend Python
│   ├── lambdas/                   # Funciones Lambda
│   ├── layers/                    # Lambda Layers (dependencias compartidas)
│   └── utils/                     # Utilidades compartidas
│
├── frontend/                      # Frontend Python
│   ├── src/                       # Código fuente
│   └── public/                    # Archivos estáticos
│
├── deployment/                    # Despliegue
│   └── terraform/                 # Infraestructura como código
│       ├── modules/rds/           # Módulo de RDS
│       └── environments/          # Configuraciones por entorno
│           ├── dev/
│           ├── pre/
│           └── pro/
│
├── docs/                          # Documentación
├── tests/                         # Tests
└── README.md                      # Este archivo
```

## 🗄️ Base de Datos

### Nomenclatura de Tablas

**Formato:** `identity-manager-<función>-tbl`

Todas las tablas siguen el estándar de nomenclatura corporativo con guiones y sufijo `-tbl`.

### Esquema Principal (PostgreSQL)

El esquema incluye **10 tablas** optimizadas:

1. **identity-manager-models-tbl** - Catálogo de modelos LLM
2. **identity-manager-applications-tbl** - Aplicaciones del sistema
3. **identity-manager-modules-tbl** - Módulos de aplicaciones
4. **identity-manager-profiles-tbl** - Perfiles (grupo + app + modelo)
5. **identity-manager-tokens-tbl** - Tokens JWT emitidos
6. **identity-manager-permission-types-tbl** - Tipos de permisos
7. **identity-manager-app-permissions-tbl** - Permisos sobre aplicaciones
8. **identity-manager-module-permissions-tbl** - Permisos sobre módulos
9. **identity-manager-config-tbl** - Configuración de la aplicación
10. **identity-manager-audit-tbl** - Auditoría de operaciones

### Características del Diseño

- ✅ **Sin duplicación de Cognito** - Solo referencias con `cognito_user_id` y `cognito_email`
- ✅ **Optimizado para bajo volumen** - Sin índices innecesarios
- ✅ **3 vistas útiles** - Para consultas comunes
- ✅ **Triggers automáticos** - Para `updated_at`

## 🚀 Despliegue

### Opción 1: Terraform (Recomendado)

Terraform automatiza la creación de RDS, configuración de seguridad, y ejecución de scripts SQL.

```bash
cd deployment/terraform/environments/dev

# 1. Configurar variables
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tu VPC ID y configuración

# 2. Inicializar Terraform
terraform init

# 3. Desplegar infraestructura
terraform plan
terraform apply
```

**Terraform creará automáticamente:**
- ✅ RDS PostgreSQL instance
- ✅ Security groups y networking
- ✅ Secrets Manager con credenciales
- ✅ Ejecutará todos los scripts SQL (schema + seeds)

Ver [deployment/terraform/README.md](deployment/terraform/README.md) para más detalles.

### Opción 2: Manual (PostgreSQL)

## 🗄️ Instalación Manual de la Base de Datos

### Nomenclatura de Base de Datos

**Formato:** `<aplicacion>_<entorno>_rds`

- **Aplicación:** identity-manager → `identity_manager` (guiones reemplazados por guiones bajos)
- **Entorno:** dev / pre / pro

**Ejemplos:**
- `identity_manager_dev_rds` - Desarrollo
- `identity_manager_pre_rds` - Preproducción
- `identity_manager_pro_rds` - Producción

> **Nota:** RDS no admite guiones "-" en nombres de BD. Se reemplazan por guiones bajos "_".

### Orden de Ejecución

```bash
# Definir el entorno (dev, pre, pro)
DB_NAME="identity_manager_dev_rds"

# 1. Crear el esquema (tablas, vistas, triggers) - VERSIÓN 4.0 CON NOMENCLATURA ESTÁNDAR
psql -h <host> -U <user> -d $DB_NAME -f database/schema/identity_manager_schema_v2.sql

# 2. Cargar tipos de permisos
psql -h <host> -U <user> -d $DB_NAME -f database/seeds/insert_permission_types_v2.sql

# 3. Cargar aplicaciones
psql -h <host> -U <user> -d $DB_NAME -f database/seeds/insert_applications_v2.sql

# 4. Cargar modelos
psql -h <host> -U <user> -d $DB_NAME -f database/seeds/insert_models_v2.sql

# 5. Cargar módulos
psql -h <host> -U <user> -d $DB_NAME -f database/seeds/insert_modules_v2.sql
```

### Archivos Disponibles

**Esquemas:**
- `identity_manager_schema_v2.sql` - **RECOMENDADO** - Versión 4.0 con nomenclatura estándar
- `identity_manager_schema.sql` - Versión 3.0 (legacy, nombres sin guiones)

**Seeds:**
- Archivos `*_v2.sql` - **RECOMENDADOS** - Para usar con schema v2
- Archivos sin sufijo - Para usar con schema v1 (legacy)

## 📋 Aplicaciones Configuradas

1. **kb-agent** - Agente de Conocimiento
2. **bedrock-proxy** - Proxy Bedrock
3. **capacity-mgmt** - Gestor de Capacidad
4. **identity-mgmt** - Gestor de Identidades
5. **bedrock-dashboard** - Control de Uso Bedrock
6. **kb-agent-dashboard** - Control de Uso Knowledge Base
7. **test-planner** - Planificador de Pruebas
8. **user-mgmt-tools** - Herramientas CLI para gestión de usuarios
9. **cline** - Agente de codificación Cline

## 🤖 Modelos de Bedrock (EU)

1. **Claude Sonnet 4.5** - `eu.anthropic.claude-sonnet-4-5-20250929-v1:0`
2. **Claude Sonnet 4.6** - `eu.anthropic.claude-sonnet-4-6`
3. **Claude Haiku 4.5** - `eu.anthropic.claude-haiku-4-5-20251001-v1:0`

## 🔧 Módulos de Aplicaciones

### kb-agent
- **chat** - Módulo de chat interactivo
- **document-management** - Gestión de documentos

## 🔐 Integración con AWS Cognito

### Atributos Requeridos

Los usuarios en Cognito deben tener:
- `email` (atributo estándar) - usado como username
- `custom:person` (atributo personalizado) - nombre y apellidos

### Configuración

Los parámetros de configuración se almacenan en la tabla `app_configuration`:
- `db_secret_name` - Nombre del secreto en AWS Secrets Manager
- `cognito_user_pool_id` - ID del User Pool de Cognito
- `cognito_region` - Región de AWS

## 🛠️ Tecnologías

- **Base de Datos:** PostgreSQL (AWS RDS)
- **Backend:** Python + AWS Lambda
- **Frontend:** Python
- **Autenticación:** AWS Cognito
- **IA:** AWS Bedrock

## 📝 Tipos de Permisos

- **Read-only** (nivel 10) - Solo lectura
- **Write** (nivel 50) - Lectura y escritura
- **Admin** (nivel 100) - Control total

## 🚀 Despliegue con Terraform

El proyecto incluye infraestructura como código (IaC) con Terraform para automatizar el despliegue:

### Características
- ✅ **Creación automática de RDS** PostgreSQL
- ✅ **Gestión de credenciales** con AWS Secrets Manager
- ✅ **Configuración de red** (Security Groups, Subnets)
- ✅ **Inicialización automática** de esquema y datos
- ✅ **Múltiples entornos** (dev, pre, pro)
- ✅ **Backups y monitoring** configurables

### Quick Start

```bash
cd deployment/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars
terraform init
terraform apply
```

Ver documentación completa en [deployment/terraform/README.md](deployment/terraform/README.md)

## 🔄 Próximos Pasos

1. ✅ Desplegar infraestructura con Terraform
2. Implementar funciones Lambda para el backend
3. Desarrollar frontend de gestión
4. Configurar Lambda triggers en Cognito
5. Implementar API REST
6. Configurar CI/CD

## 📚 Documentación Adicional

Ver carpeta `docs/` para documentación detallada.

## 🧪 Tests

Los tests se encuentran en la carpeta `tests/`.

## 📄 Licencia

[Especificar licencia]

## 👥 Contribuidores

[Especificar contribuidores]
