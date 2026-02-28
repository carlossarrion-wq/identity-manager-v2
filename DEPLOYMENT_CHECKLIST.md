# ✅ Checklist de Despliegue - Identity Manager v2

## 📋 Pre-requisitos

### Software Requerido
- [ ] Terraform >= 1.0 instalado
- [ ] AWS CLI configurado con credenciales válidas
- [ ] PostgreSQL client (psql) instalado
- [ ] jq instalado para procesamiento JSON

### Permisos AWS Requeridos
- [ ] Permisos para crear RDS instances
- [ ] Permisos para VPC/Subnets/Security Groups
- [ ] Permisos para AWS Secrets Manager
- [ ] Permisos para IAM (crear roles de monitoring)

### Información Necesaria
- [ ] VPC ID donde desplegar RDS
- [ ] Subnet IDs (o tags para auto-discovery)
- [ ] CIDR blocks permitidos para acceso a RDS

## 🗄️ Archivos de Base de Datos

### Esquema v2 (Recomendado)
- [x] `database/schema/identity_manager_schema_v2.sql` - Esquema con nomenclatura estándar
- [x] 10 tablas con formato `identity-manager-<función>-tbl`
- [x] 3 vistas útiles
- [x] Triggers automáticos
- [x] Datos de ejemplo incluidos

### Seeds v2
- [x] `database/seeds/insert_permission_types_v2.sql` - 3 tipos de permisos
- [x] `database/seeds/insert_applications_v2.sql` - 9 aplicaciones
- [x] `database/seeds/insert_models_v2.sql` - 3 modelos EU
- [x] `database/seeds/insert_modules_v2.sql` - 2 módulos de kb-agent

## 🏗️ Infraestructura Terraform

### Módulo RDS
- [x] `deployment/terraform/modules/rds/main.tf` - Recursos principales
- [x] `deployment/terraform/modules/rds/variables.tf` - Variables configurables
- [x] `deployment/terraform/modules/rds/outputs.tf` - Outputs útiles
- [x] Null resource para inicialización automática de BD
- [x] Secrets Manager con nomenclatura estándar

### Entorno Dev
- [x] `deployment/terraform/environments/dev/main.tf` - Configuración
- [x] `deployment/terraform/environments/dev/variables.tf` - Variables
- [x] `deployment/terraform/environments/dev/outputs.tf` - Outputs
- [x] `deployment/terraform/environments/dev/terraform.tfvars.example` - Plantilla

### Documentación
- [x] `deployment/terraform/README.md` - Guía completa de Terraform
- [x] `README.md` - Documentación principal actualizada

## 📝 Nomenclaturas Aplicadas

### Base de Datos
- [x] Formato: `identity_manager_<env>_rds`
- [x] Ejemplo dev: `identity_manager_dev_rds`

### Tablas
- [x] Formato: `identity-manager-<función>-tbl`
- [x] 10 tablas con nomenclatura estándar

### Secrets Manager
- [x] Formato: `identity-mgmt-<env>-db-admin`
- [x] Tags organizados (Application, SecretType, AccessLevel)

### Recursos AWS
- [x] RDS: `identity-manager-<env>-rds`
- [x] Security Group: `identity-manager-<env>-rds-sg`

## 🚀 Pasos para Desplegar

### 1. Preparación
```bash
cd deployment/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
```

### 2. Editar terraform.tfvars
- [ ] Configurar `vpc_id`
- [ ] Configurar `subnet_ids` (opcional)
- [ ] Configurar `allowed_cidr_blocks`
- [ ] Revisar configuración de RDS (instance_class, storage, etc.)

### 3. Inicializar Terraform
```bash
terraform init
```
- [ ] Verificar que se descarguen los providers correctamente

### 4. Validar Configuración
```bash
terraform validate
```
- [ ] Verificar que no hay errores de sintaxis

### 5. Planificar Despliegue
```bash
terraform plan
```
- [ ] Revisar recursos que se crearán
- [ ] Verificar nomenclaturas
- [ ] Confirmar configuración de RDS

### 6. Aplicar Infraestructura
```bash
terraform apply
```
- [ ] Confirmar con "yes"
- [ ] Esperar ~10-15 minutos para creación de RDS
- [ ] Verificar que scripts SQL se ejecuten correctamente

### 7. Verificar Despliegue
```bash
# Ver outputs
terraform output

# Verificar secreto
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw secret_name) \
  --query SecretString --output text | jq .
```

### 8. Probar Conexión
```bash
SECRET=$(aws secretsmanager get-secret-value --secret-id $(terraform output -raw secret_name) --query SecretString --output text)
DB_HOST=$(echo $SECRET | jq -r .host)
DB_USER=$(echo $SECRET | jq -r .username)
DB_PASS=$(echo $SECRET | jq -r .password)
DB_NAME=$(echo $SECRET | jq -r .dbname)

PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c '\dt'
```
- [ ] Verificar que se listan las 10 tablas
- [ ] Verificar nomenclatura de tablas

### 9. Verificar Datos
```bash
# Verificar tipos de permisos
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c 'SELECT * FROM "identity-manager-permission-types-tbl";'

# Verificar aplicaciones
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c 'SELECT * FROM "identity-manager-applications-tbl";'

# Verificar modelos
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c 'SELECT * FROM "identity-manager-models-tbl";'
```
- [ ] Verificar 3 tipos de permisos
- [ ] Verificar 9 aplicaciones
- [ ] Verificar 3 modelos
- [ ] Verificar 2 módulos de kb-agent

## ⚠️ Consideraciones Importantes

### Seguridad
- [ ] RDS está en subnets privadas
- [ ] Security Group solo permite acceso desde CIDRs específicos
- [ ] Credenciales almacenadas en Secrets Manager
- [ ] Encriptación en reposo habilitada

### Backups
- [ ] Backup retention configurado (3 días en dev)
- [ ] Backup window configurado
- [ ] Maintenance window configurado

### Monitoring
- [ ] CloudWatch logs habilitados (postgresql, upgrade)
- [ ] Enhanced monitoring configurado según entorno

### Costos
- [ ] Instancia db.t3.micro en dev (~$15-20/mes)
- [ ] Storage 20GB gp3 (~$2-3/mes)
- [ ] Backups incluidos en retention period

## 🔧 Troubleshooting

### Si falla la inicialización de BD
1. Verificar que psql está instalado: `which psql`
2. Verificar que jq está instalado: `which jq`
3. Aumentar sleep en null_resource (de 30 a 60 segundos)
4. Re-ejecutar: `terraform taint module.rds.null_resource.init_database && terraform apply`

### Si no se puede conectar a RDS
1. Verificar security group permite tu IP
2. Verificar que estás en la VPC correcta
3. Usar bastion host si RDS no es público

### Si hay error con Secrets Manager
1. Esperar unos segundos (se crea después de RDS)
2. Verificar permisos IAM para Secrets Manager

## ✅ Checklist Final

- [ ] Todos los pre-requisitos cumplidos
- [ ] terraform.tfvars configurado correctamente
- [ ] `terraform plan` ejecutado sin errores
- [ ] `terraform apply` completado exitosamente
- [ ] RDS instance creada y disponible
- [ ] Secrets Manager creado con credenciales
- [ ] Scripts SQL ejecutados correctamente
- [ ] 10 tablas creadas con nomenclatura correcta
- [ ] Datos iniciales cargados (permisos, apps, modelos, módulos)
- [ ] Conexión a BD verificada
- [ ] Queries de prueba ejecutadas correctamente

## 🎉 ¡Listo para Producción!

Una vez completado este checklist, la base de datos está lista para:
- Desarrollo de backend (Lambda functions)
- Desarrollo de frontend
- Integración con Cognito
- Implementación de lógica de negocio

## 📚 Próximos Pasos

1. Configurar AWS Cognito User Pool
2. Implementar funciones Lambda para API
3. Desarrollar frontend de gestión
4. Configurar CI/CD pipeline
5. Replicar para entornos pre y pro
