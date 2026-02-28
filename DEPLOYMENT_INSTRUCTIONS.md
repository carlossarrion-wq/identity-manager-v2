# 🚀 Identity Manager - Instrucciones de Despliegue

## ✅ Estado Actual del Despliegue

### Infraestructura Desplegada:
- ✅ **RDS PostgreSQL 15.16** en RAG-VPC
- ✅ **Secrets Manager** con credenciales
- ✅ **Security Groups** configurados
- ✅ **Subnets privadas** en RAG-VPC

### Pendiente:
- ⏳ Inicialización de base de datos desde EC2

---

## 📋 Paso Final: Inicializar Base de Datos

### Opción 1: Usando el Script Automatizado (RECOMENDADO)

```bash
# 1. Conectar a EC2
ssh -i ~/.ssh/ec2_new_key ec2-user@18.202.140.248

# 2. Copiar archivos desde tu máquina local (en otra terminal)
scp -i ~/.ssh/ec2_new_key -r database scripts ec2-user@18.202.140.248:~/

# 3. En EC2, dar permisos de ejecución
chmod +x ~/scripts/init_db_from_ec2.sh

# 4. Ejecutar el script
~/scripts/init_db_from_ec2.sh
```

### Opción 2: Manual

```bash
# 1. Conectar a EC2
ssh -i ~/.ssh/ec2_new_key ec2-user@18.202.140.248

# 2. Obtener credenciales
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id identity-mgmt-dev-db-admin \
  --region eu-west-1 \
  --query SecretString --output text)

DB_HOST=$(echo $SECRET | jq -r .host)
DB_PORT=$(echo $SECRET | jq -r .port)
DB_NAME=$(echo $SECRET | jq -r .dbname)
DB_USER=$(echo $SECRET | jq -r .username)
DB_PASS=$(echo $SECRET | jq -r .password)

export PGPASSWORD=$DB_PASS

# 3. Ejecutar scripts SQL
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/schema/identity_manager_schema_v2.sql

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_permission_types_v2.sql

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_applications_v2.sql

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_models_v2.sql

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_modules_v2.sql
```

---

## 🔍 Verificación

### Ver información del RDS:

```bash
cd deployment/terraform/environments/dev
terraform output
```

### Conectarse a la base de datos:

```bash
# Desde EC2
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id identity-mgmt-dev-db-admin \
  --region eu-west-1 \
  --query SecretString --output text)

DB_HOST=$(echo $SECRET | jq -r .host)
DB_USER=$(echo $SECRET | jq -r .username)
DB_NAME=$(echo $SECRET | jq -r .dbname)
export PGPASSWORD=$(echo $SECRET | jq -r .password)

psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

### Verificar tablas y datos:

```sql
-- Listar tablas
\dt

-- Contar registros
SELECT 
  'permission_types' as table_name, 
  COUNT(*) as records 
FROM "identity-manager-permission-types-tbl"
UNION ALL
SELECT 'applications', COUNT(*) FROM "identity-manager-applications-tbl"
UNION ALL
SELECT 'models', COUNT(*) FROM "identity-manager-models-tbl"
UNION ALL
SELECT 'modules', COUNT(*) FROM "identity-manager-modules-tbl"
ORDER BY table_name;
```

---

## 📊 Información de la Infraestructura

### VPC y Networking:
- **VPC**: RAG-VPC (vpc-04ba39cd0772a280b)
- **CIDR**: 10.0.0.0/16
- **Subnets Privadas**: 
  - subnet-09d9eef6deec49835 (eu-west-1a)
  - subnet-095c40811320a693a (eu-west-1b)

### RDS:
- **Nombre**: identity-manager-dev-rds
- **Engine**: PostgreSQL 15.16
- **Instancia**: db.t3.micro
- **Storage**: 20GB gp3
- **Backups**: 3 días
- **Encriptación**: Habilitada

### Secrets Manager:
- **Nombre**: identity-mgmt-dev-db-admin
- **Región**: eu-west-1

---

## 🛠️ Gestión de la Infraestructura

### Ver estado actual:
```bash
cd deployment/terraform/environments/dev
terraform show
```

### Actualizar infraestructura:
```bash
cd deployment/terraform/environments/dev
terraform plan
terraform apply
```

### Destruir infraestructura:
```bash
cd deployment/terraform/environments/dev
terraform destroy
```

---

## 📝 Estructura de la Base de Datos

### Tablas Principales:
1. **identity-manager-permission-types-tbl** (3 registros)
   - Tipos de permisos: read, write, admin

2. **identity-manager-applications-tbl** (9 registros)
   - Aplicaciones del sistema

3. **identity-manager-models-tbl** (3 registros)
   - Modelos de IA de EU

4. **identity-manager-modules-tbl** (2 registros)
   - Módulos del sistema

5. **identity-manager-users-tbl**
   - Usuarios del sistema

6. **identity-manager-roles-tbl**
   - Roles y permisos

7. **identity-manager-user-roles-tbl**
   - Relación usuarios-roles

8. **identity-manager-role-permissions-tbl**
   - Permisos por rol

9. **identity-manager-audit-log-tbl**
   - Auditoría de cambios

10. **identity-manager-sessions-tbl**
    - Sesiones activas

### Vistas Útiles:
- **v_user_permissions**: Permisos efectivos por usuario
- **v_role_summary**: Resumen de roles y permisos
- **v_audit_trail**: Historial de auditoría

---

## 🔐 Seguridad

- ✅ RDS en subnets privadas
- ✅ Credenciales en Secrets Manager
- ✅ Encriptación en reposo (KMS)
- ✅ Encriptación en tránsito (SSL)
- ✅ Security Groups restrictivos
- ✅ Backups automáticos
- ✅ CloudWatch Logs habilitados

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs de CloudWatch
2. Verificar Security Groups
3. Comprobar estado de RDS en consola AWS
4. Revisar terraform state

---

## 🎉 ¡Listo!

Una vez ejecutado el script de inicialización, la base de datos estará completamente configurada y lista para usar.
