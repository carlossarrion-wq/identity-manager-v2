# Solución de Conectividad - Lambda + RDS + Cognito

## 🔍 Problema Identificado

### Por qué la Opción 1 (Lambda SIN VPC + RDS Público) NO funcionaba:

1. **RDS estaba en subnets PRIVADAS**:
   - `subnet-09d9eef6deec49835` (eu-west-1a) - PRIVADA
   - `subnet-095c40811320a693a` (eu-west-1b) - PRIVADA
   - Estas subnets NO tienen ruta a Internet Gateway (0.0.0.0/0 → igw-xxx)

2. **Aunque `publicly_accessible = true`**:
   - El RDS no puede recibir conexiones desde internet
   - Las subnets privadas solo tienen rutas locales (10.0.0.0/16)

3. **Route Table Principal de la VPC**:
   ```
   10.0.0.0/16     → local
   172.31.0.0/16   → peering (otra VPC)
   ```
   ❌ NO hay ruta: `0.0.0.0/0 → igw-06db3124b57528ff9`

---

## ✅ Solución Implementada

### Arquitectura Final (Opción 1 Corregida):

```
┌─────────────────────────────────────────┐
│           INTERNET                       │
└─────────────────────────────────────────┘
     │              │              │
     │              │              │
┌────▼────┐   ┌────▼────┐   ┌────▼────────┐
│ Lambda  │   │ Cognito │   │   Secrets   │
│(Sin VPC)│   │(Público)│   │  Manager    │
└────┬────┘   └─────────┘   └─────────────┘
     │
     │ (Acceso directo via Internet)
     │
┌────▼──────────────────────────────────────┐
│         VPC (vpc-04ba39cd0772a280b)       │
│                                            │
│  ┌──────────────────────────────────┐    │
│  │  SUBNETS PÚBLICAS (con IGW)      │    │
│  │  - subnet-038b1f57392415153      │    │
│  │  - subnet-0e984b3f275d482f1      │    │
│  │                                   │    │
│  │  ┌────────────────────────────┐  │    │
│  │  │  RDS PostgreSQL            │  │    │
│  │  │  publicly_accessible=true  │  │    │
│  │  │  Security Group: 0.0.0.0/0 │  │    │
│  │  └────────────────────────────┘  │    │
│  └──────────────────────────────────┘    │
│                                            │
│  Route Table: 0.0.0.0/0 → igw-xxx        │
└────────────────────────────────────────────┘
```

### Cambios Realizados:

1. **RDS movido a subnets PÚBLICAS**:
   ```hcl
   subnet_ids = [for s in data.aws_subnet.rag_public : s.id]
   # subnet-038b1f57392415153, subnet-0e984b3f275d482f1
   ```

2. **Lambda SIN VPC**:
   ```hcl
   # vpc_config comentado
   # Lambda tiene acceso directo a internet
   ```

3. **Security Group del RDS**:
   ```hcl
   ingress {
     from_port   = 5432
     to_port     = 5432
     protocol    = "tcp"
     cidr_blocks = ["0.0.0.0/0"]  # Permite desde internet
   }
   ```

---

## 💰 Costos Mensuales

| Componente | Costo |
|------------|-------|
| Lambda (sin VPC) | $0 (capa gratuita) |
| RDS db.t3.micro | ~$15/mes |
| Cognito | $0 (hasta 50K MAU) |
| Secrets Manager | ~$0.40/mes |
| **TOTAL** | **~$15.40/mes** |

**Ahorro vs NAT Gateway**: $32/mes

---

## 🔒 Seguridad

Aunque el RDS es públicamente accesible:

1. ✅ **SSL/TLS obligatorio** (`sslmode=require`)
2. ✅ **Credenciales en Secrets Manager** (rotación automática posible)
3. ✅ **Contraseña fuerte** (32 caracteres aleatorios)
4. ✅ **Security Group** (aunque permite 0.0.0.0/0, requiere autenticación)
5. ✅ **Autenticación PostgreSQL** requerida
6. ✅ **Logs de CloudWatch** habilitados
7. ✅ **Backups automáticos** (3 días retención)

### Mejoras de Seguridad Adicionales (Opcional):

```hcl
# Restringir a rangos de IP de AWS Lambda en eu-west-1
cidr_blocks = [
  "3.248.0.0/13",    # Lambda IPs eu-west-1
  "18.200.0.0/13",   # Lambda IPs eu-west-1
  # ... más rangos
]
```

---

## 📋 Pasos de Implementación

### 1. Destruir RDS actual (en subnets privadas)
```bash
cd deployment/terraform/environments/dev
terraform destroy -target=module.rds.aws_db_instance.main -auto-approve
```

### 2. Destruir DB Subnet Group
```bash
terraform destroy -target=module.rds.aws_db_subnet_group.main -auto-approve
```

### 3. Recrear infraestructura
```bash
terraform apply -auto-approve
```

### 4. Reinicializar base de datos
```bash
# Desde EC2 en la misma VPC
ssh ec2-user@18.202.140.248
cd /home/ec2-user
./init_db_uuid.sh
```

### 5. Probar conexiones
```bash
# Test BD
curl -X POST https://vgrajswesgyujgxpw5g65tw5py0kihum.lambda-url.eu-west-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"operation": "get_config"}' | jq .

# Test Cognito
curl -X POST https://vgrajswesgyujgxpw5g65tw5py0kihum.lambda-url.eu-west-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"operation": "list_groups"}' | jq .
```

---

## 🏗️ Para Producción

En producción, usar arquitectura más segura:

### Opción A: Lambda EN VPC + NAT Gateway
```
Costo: +$32/mes
Seguridad: ⭐⭐⭐⭐⭐
RDS: Completamente privado
```

### Opción B: Lambda EN VPC + VPC Endpoints
```
Costo: +$7/mes por endpoint
Seguridad: ⭐⭐⭐⭐
Nota: Cognito NO tiene VPC Endpoint
```

---

## 📊 Verificación de Subnets

### Subnets PRIVADAS (sin IGW):
```bash
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-04ba39cd0772a280b" \
  --query 'RouteTables[*].{RT:RouteTableId,Routes:Routes,Subnets:Associations[*].SubnetId}'
```

### Subnets PÚBLICAS (con IGW):
```bash
# subnet-038b1f57392415153
# subnet-0e984b3f275d482f1
# Route: 0.0.0.0/0 → igw-06db3124b57528ff9
```

---

## ✅ Ventajas de esta Solución

1. **Económica**: ~$15/mes (sin NAT Gateway)
2. **Simple**: Sin complejidad de VPC para Lambda
3. **Rápida**: Sin cold start de VPC en Lambda
4. **Funcional**: Acceso a Cognito, RDS y Secrets Manager
5. **Segura**: Múltiples capas de seguridad

---

## ⚠️ Consideraciones

1. **Solo para DEV/TEST**: En producción usar NAT Gateway
2. **IPs dinámicas**: Las IPs de Lambda cambian, por eso Security Group permite 0.0.0.0/0
3. **Backups**: Configurar backups automáticos antes de producción
4. **Monitoreo**: Habilitar CloudWatch Alarms en producción

---

## 🔄 Rollback (si es necesario)

Para volver a la arquitectura anterior (Lambda EN VPC):

```hcl
# main.tf
module "rds" {
  subnet_ids = [for s in data.aws_subnet.rag_private : s.id]
}

module "lambda" {
  vpc_config = {
    subnet_ids         = [for s in data.aws_subnet.rag_private : s.id]
    security_group_ids = [module.rds.security_group_id]
  }
}
```

Luego crear NAT Gateway para acceso a Cognito.
