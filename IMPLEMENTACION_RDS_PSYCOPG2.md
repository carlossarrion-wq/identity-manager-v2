# Implementación de Conexión RDS con psycopg2

## 📋 Resumen Ejecutivo

Se ha implementado exitosamente la conexión a PostgreSQL RDS usando **psycopg2-binary** con el patrón **Connection Pool Singleton**, siguiendo la estrategia del proyecto **Dashboard Consultas RAG** que utiliza **Klayers Lambda Layer**.

## 🎯 Solución Implementada

### Estrategia: Klayers Lambda Layer

**Layer ARN**: `arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2`

**Ventajas**:
- ✅ Sin necesidad de compilación local
- ✅ Mantenido públicamente por la comunidad
- ✅ Probado en producción (Dashboard Consultas RAG)
- ✅ Compatible con Python 3.12 y AWS Lambda
- ✅ Package más ligero (psycopg2 no incluido en el ZIP)

## 📁 Archivos Implementados/Modificados

### 1. DatabaseService - Connection Pool Singleton
**Archivo**: `backend/lambdas/identity-mgmt-api/services/database_service.py`

```python
class DatabaseService:
    """
    Servicio para gestionar conexiones a PostgreSQL RDS.
    Implementa Connection Pool Singleton optimizado para Lambda.
    """
    _pool = None  # Singleton pool
    _secrets_cache = None  # Caché de credenciales
    _cache_timestamp = None
    CACHE_TTL = 300  # 5 minutos
```

**Características**:
- Connection Pool Singleton (1 conexión por contenedor Lambda)
- Secrets Manager con caché (TTL 5 minutos)
- Context Manager para transacciones automáticas
- Métodos helper: `execute_query()` y `execute_update()`
- Timeouts configurados: 10s conexión, 30s statement
- SSL obligatorio (sslmode='require')
- Logging completo para trazabilidad

### 2. Terraform - Lambda con Klayers
**Archivo**: `deployment/terraform/modules/lambda/main.tf`

```hcl
resource "aws_lambda_function" "api" {
  # ... configuración ...
  
  # Lambda Layer - Klayers psycopg2-binary
  layers = [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"
  ]
  
  # ... resto de configuración ...
}
```

### 3. Script de Empaquetado Optimizado
**Archivo**: `scripts/package_lambda.sh`

```bash
# Excluir psycopg2-binary ya que viene del Klayers Lambda Layer
grep -v "psycopg2-binary" "$BUILD_DIR/requirements.txt" > "$BUILD_DIR/requirements-no-psycopg2.txt"
```

**Resultado**: Package ~49MB (sin psycopg2-binary)

### 4. Scripts de Backup para Layer Manual
**Archivos creados**:
- `scripts/create_psycopg2_layer.sh` - Crear layer localmente
- `scripts/create_psycopg2_layer_docker.sh` - Crear layer con Docker

## 📊 Comparativa de Estrategias

| Proyecto | Lenguaje | Librería | Estrategia | Layer |
|----------|----------|----------|------------|-------|
| **Gestión Demanda** | Node.js | `pg` v8.11.3 | npm package | No |
| **Dashboard Consultas RAG** | Python 3.12 | `psycopg2-binary` 2.9.9 | Klayers Layer | Sí |
| **Identity Manager** | Python 3.12 | `psycopg2-binary` 2.9.9 | Klayers Layer | Sí |

### Patrón Común: Connection Pool Singleton

Todos los proyectos implementan el mismo patrón:

**Node.js (Gestión Demanda)**:
```javascript
const pool = new Pool({
  max: 1,  // 1 conexión por contenedor
  connectionTimeoutMillis: 10000,
  idleTimeoutMillis: 30000
});
```

**Python (Identity Manager)**:
```python
_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=1,  # 1 conexión por contenedor
    connect_timeout=10,
    options='-c statement_timeout=30000'
)
```

## 🔧 Configuración de Infraestructura

### VPC Configuration
- **VPC**: RAG-VPC (`vpc-04ba39cd0772a280b`)
- **Subnets**: 
  - `subnet-09d9eef6deec49835`
  - `subnet-095c40811320a693a`
- **Security Group**: `sg-07cc4f3c939e3b103` (acceso a RDS)

### Secrets Manager
- **DB Credentials**: `identity-mgmt-dev-db-admin`
- **JWT Secret**: `identity-mgmt-dev-key-access`

### IAM Permissions
```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": [
    "arn:aws:secretsmanager:eu-west-1:*:secret:identity-mgmt-dev-db-admin-*",
    "arn:aws:secretsmanager:eu-west-1:*:secret:identity-mgmt-dev-key-access-*"
  ]
}
```

## 🚀 Despliegue

### Comandos Ejecutados

```bash
# 1. Empaquetar Lambda (sin psycopg2-binary)
./scripts/package_lambda.sh

# 2. Desplegar con Terraform
cd deployment/terraform/environments/dev
terraform apply -auto-approve
```

### Estado del Despliegue

```bash
$ aws lambda get-function --function-name identity-mgmt-dev-api-lmbd
Status: Active ✓
LastUpdateStatus: Successful ✓
Runtime: python3.12 ✓
Layers: arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2 ✓
```

## 📝 Uso del DatabaseService

### Ejemplo 1: Query Simple

```python
from services.database_service import DatabaseService

# Ejecutar query
results = DatabaseService.execute_query(
    "SELECT * FROM users WHERE active = %s",
    (True,)
)

for row in results:
    print(f"User: {row['username']}")
```

### Ejemplo 2: Transacción con Context Manager

```python
from services.database_service import DatabaseService

# Transacción automática
with DatabaseService.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (username, email) VALUES (%s, %s)",
            ('john', 'john@example.com')
        )
        cursor.execute(
            "INSERT INTO profiles (user_id, name) VALUES (%s, %s)",
            (cursor.lastrowid, 'John Doe')
        )
    # Commit automático al salir del context manager
```

### Ejemplo 3: Update/Insert

```python
from services.database_service import DatabaseService

# Ejecutar update
rows_affected = DatabaseService.execute_update(
    "UPDATE users SET last_login = NOW() WHERE username = %s",
    ('john',)
)

print(f"Rows updated: {rows_affected}")
```

## 🔒 Mejores Prácticas Implementadas

### 1. Connection Pooling
- ✅ 1 conexión por contenedor Lambda
- ✅ Reutilización entre invocaciones
- ✅ Cierre automático en caso de error

### 2. Timeout Management
- ✅ 10 segundos para establecer conexión
- ✅ 30 segundos para ejecutar statements
- ✅ Previene conexiones colgadas

### 3. SSL/TLS
- ✅ `sslmode='require'` obligatorio
- ✅ Conexiones seguras a RDS

### 4. Secrets Management
- ✅ Credenciales desde Secrets Manager
- ✅ Caché de 5 minutos (reduce llamadas a AWS)
- ✅ Rotación automática de secretos

### 5. Error Handling
- ✅ Rollback automático en errores
- ✅ Logging de excepciones
- ✅ Reintentos en caso de pool agotado

### 6. Context Managers
- ✅ Liberación automática de conexiones
- ✅ Commit/Rollback automático
- ✅ Código más limpio y seguro

## 🧪 Testing

### Test de Conexión

```python
def test_database_connection():
    """Test básico de conexión a RDS"""
    result = DatabaseService.execute_query("SELECT version()")
    assert result is not None
    assert len(result) > 0
    print(f"PostgreSQL version: {result[0]['version']}")
```

### Verificar desde Lambda

```bash
# Obtener Lambda URL
LAMBDA_URL=$(aws lambda get-function-url-config \
  --function-name identity-mgmt-dev-api-lmbd \
  --region eu-west-1 \
  --query 'FunctionUrl' \
  --output text)

# Test endpoint
curl "${LAMBDA_URL}health"
```

### Ver Logs

```bash
# Tail logs en tiempo real
aws logs tail /aws/lambda/identity-mgmt-dev-api-lmbd --follow

# Filtrar errores
aws logs filter-log-events \
  --log-group-name /aws/lambda/identity-mgmt-dev-api-lmbd \
  --filter-pattern "ERROR"
```

## 📚 Referencias

### Klayers
- **GitHub**: https://github.com/keithrozario/Klayers
- **Documentación**: https://github.com/keithrozario/Klayers#using-the-layers
- **Layers disponibles**: https://api.klayers.cloud/api/v2/p3.12/layers/latest/eu-west-1/html

### psycopg2
- **Documentación**: https://www.psycopg.org/docs/
- **Connection Pool**: https://www.psycopg.org/docs/pool.html
- **Best Practices**: https://www.psycopg.org/docs/usage.html

### AWS Lambda
- **Layers**: https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html
- **VPC**: https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html
- **Best Practices**: https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html

## 🎯 Próximos Pasos

### 1. Testing Completo
- [ ] Test de conexión a RDS
- [ ] Test de queries básicas
- [ ] Test de transacciones
- [ ] Test de manejo de errores
- [ ] Test de performance

### 2. Monitoreo
- [ ] Configurar CloudWatch Alarms
- [ ] Dashboard de métricas
- [ ] Alertas de errores
- [ ] Tracking de conexiones

### 3. Optimización
- [ ] Ajustar timeouts según carga
- [ ] Optimizar queries
- [ ] Implementar caché de queries frecuentes
- [ ] Revisar índices en RDS

### 4. Documentación
- [ ] API documentation
- [ ] Ejemplos de uso
- [ ] Troubleshooting guide
- [ ] Runbook operacional

## ✅ Checklist de Implementación

- [x] DatabaseService con Connection Pool Singleton
- [x] Terraform configurado con Klayers
- [x] Script de empaquetado optimizado
- [x] Lambda desplegada en AWS
- [x] VPC y Security Groups configurados
- [x] Secrets Manager integrado
- [x] IAM permissions configuradas
- [x] Logging implementado
- [ ] Testing completo
- [ ] Monitoreo configurado
- [ ] Documentación API completa

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs en CloudWatch
2. Verificar configuración de VPC/Security Groups
3. Validar credenciales en Secrets Manager
4. Consultar documentación de Klayers

---

**Fecha de Implementación**: 28 de Febrero de 2026
**Versión**: 1.0.0
**Estado**: ✅ Implementado y Desplegado
