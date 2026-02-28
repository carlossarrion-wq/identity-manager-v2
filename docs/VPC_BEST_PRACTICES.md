# 🌐 Mejores Prácticas para VPCs en AWS

## ❌ NO: Una VPC por Aplicación

**Problemas:**
- ❌ **Costos elevados**: Cada VPC necesita NAT Gateways (~$32/mes cada uno)
- ❌ **Complejidad de red**: Necesitas VPC Peering o Transit Gateway entre VPCs
- ❌ **Límites AWS**: Solo 5 VPCs por región por defecto
- ❌ **Gestión compleja**: Múltiples tablas de rutas, security groups, etc.
- ❌ **Desperdicio de IPs**: Cada VPC consume un rango CIDR completo

## ✅ SÍ: VPC Compartida por Entorno

### Estrategia Recomendada: **1 VPC por Entorno**

```
Organización:
├── VPC Dev (10.0.0.0/16)
│   ├── identity-manager (subnets + security groups)
│   ├── kb-agent (subnets + security groups)
│   ├── bedrock-proxy (subnets + security groups)
│   └── otros servicios...
│
├── VPC Pre (10.1.0.0/16)
│   └── [mismas aplicaciones]
│
└── VPC Pro (10.2.0.0/16)
    └── [mismas aplicaciones]
```

### Ventajas:
- ✅ **Ahorro de costos**: 1 NAT Gateway compartido
- ✅ **Comunicación fácil**: Apps en misma VPC se comunican directamente
- ✅ **Gestión simple**: Una configuración de red por entorno
- ✅ **Seguridad por Security Groups**: Aislamiento a nivel de aplicación
- ✅ **Uso eficiente de IPs**: Mejor aprovechamiento del espacio CIDR

## 🏗️ Arquitectura Recomendada

### Opción 1: VPC Compartida (RECOMENDADO para tu caso)

```
identity-manager-dev-vpc (10.0.0.0/16)
├── Public Subnets (10.0.1.0/24, 10.0.2.0/24)
│   └── NAT Gateways, Load Balancers
│
├── Private Subnets - App Tier (10.0.10.0/24, 10.0.11.0/24)
│   ├── identity-manager (Lambda, ECS)
│   ├── kb-agent (Lambda, ECS)
│   └── bedrock-proxy (Lambda, ECS)
│
└── Private Subnets - Data Tier (10.0.20.0/24, 10.0.21.0/24)
    ├── identity-manager RDS
    ├── kb-agent RDS
    └── otros RDS
```

**Aislamiento mediante:**
- Security Groups específicos por aplicación
- NACLs si necesitas control adicional
- IAM roles separados por aplicación

### Opción 2: VPC por Aplicación (Solo si...)

**Usar SOLO si:**
- ✅ Requisitos de compliance muy estrictos
- ✅ Aplicaciones completamente independientes
- ✅ Diferentes equipos con presupuestos separados
- ✅ Necesitas aislamiento de red total

**Costos adicionales:**
- NAT Gateway: $32/mes por AZ
- Transit Gateway: $36/mes + $0.02/GB
- VPC Peering: Gratis pero complejo de gestionar

## 💰 Comparación de Costos

### Escenario: 3 Aplicaciones en eu-west-1

**Opción A: 1 VPC Compartida**
```
- 1 VPC: Gratis
- 2 NAT Gateways (HA): $64/mes
- Total: ~$64/mes
```

**Opción B: 3 VPCs Separadas**
```
- 3 VPCs: Gratis
- 6 NAT Gateways (2 por VPC): $192/mes
- Transit Gateway: $36/mes
- Data transfer: $20-50/mes
- Total: ~$248-278/mes
```

**Ahorro: ~$184/mes = $2,208/año**

## 🎯 Recomendación para Identity Manager

### Para tu caso específico:

**USAR VPC EXISTENTE** (gestion-demanda-vpc o crear una compartida)

**Razones:**
1. ✅ Identity Manager es un servicio de soporte (no core business)
2. ✅ Necesita comunicarse con otras apps (kb-agent, bedrock-proxy)
3. ✅ Bajo volumen de tráfico
4. ✅ Ahorro de costos significativo
5. ✅ Más fácil de gestionar

### Configuración Recomendada:

```hcl
# Usar VPC existente
data "aws_vpc" "shared" {
  tags = {
    Name = "shared-services-vpc"  # o gestion-demanda-vpc
  }
}

# Crear subnets específicas si es necesario
resource "aws_subnet" "identity_manager_private" {
  vpc_id     = data.aws_vpc.shared.id
  cidr_block = "10.0.50.0/24"  # Rango no usado
  
  tags = {
    Name        = "identity-manager-private"
    Application = "identity-manager"
  }
}

# Security Group específico
resource "aws_security_group" "identity_manager_rds" {
  name_prefix = "identity-manager-rds-"
  vpc_id      = data.aws_vpc.shared.id
  
  # Solo permite acceso desde apps específicas
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.identity_manager_app.id]
  }
}
```

## 📋 Decisión Final

### ¿Crear nueva VPC o usar existente?

**USAR EXISTENTE si:**
- ✅ Ya tienes VPC con espacio CIDR disponible
- ✅ Las apps necesitan comunicarse entre sí
- ✅ Quieres minimizar costos
- ✅ Equipo pequeño/mediano

**CREAR NUEVA si:**
- ✅ VPC existente está llena (sin IPs disponibles)
- ✅ Requisitos de compliance lo exigen
- ✅ Aplicación crítica que necesita aislamiento total
- ✅ Diferentes regiones AWS

## 🚀 Mi Recomendación para Ti

**Opción 1 (RECOMENDADA): Usar gestion-demanda-vpc**
```bash
# Ventajas:
- ✅ Sin costos adicionales de VPC
- ✅ Comunicación directa con otras apps
- ✅ Ya tiene NAT Gateway configurado
- ✅ Gestión centralizada

# Cambios necesarios:
- Usar data source para VPC existente
- Crear subnets específicas si es necesario
- Security Groups para aislamiento
```

**Opción 2: Crear VPC compartida nueva**
```bash
# Solo si:
- gestion-demanda-vpc no tiene espacio
- Quieres separar "gestión" de "servicios"
- Planeas migrar todas las apps a nueva VPC

# Costos:
- ~$64/mes (NAT Gateways)
```

## 🔧 ¿Qué prefieres hacer?

1. **Usar gestion-demanda-vpc** (Recomendado - $0 adicional)
2. **Crear nueva VPC compartida** (Para futuro - $64/mes)
3. **Crear VPC dedicada** (No recomendado - $64/mes + complejidad)

