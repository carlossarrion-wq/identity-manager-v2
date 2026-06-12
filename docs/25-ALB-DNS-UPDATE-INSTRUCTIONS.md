# Instrucciones para Actualizar DNS Externo

## 🔴 Problema Actual

Tu DNS externo apunta al ALB antiguo que ya no existe:

```
bedrock-proxy.leancustomer.es 
  ↓
bedrock-proxy-dev-alb-961374083.eu-west-1.elb.amazonaws.com (❌ ALB ANTIGUO - ELIMINADO)
```

## ✅ Solución: Actualizar DNS Externo

### Nuevo ALB (Activo)
```
DNS: bedrock-proxy-dev-alb-258169205.eu-west-1.elb.amazonaws.com
IPs: 99.81.61.61, 3.248.118.85, 63.35.52.224
```

### Pasos para Actualizar

**1. Accede a tu proveedor DNS externo**
   - GoDaddy, Namecheap, Route53, Cloudflare, etc.

**2. Busca el registro CNAME para `bedrock-proxy.leancustomer.es`**

**3. Actualiza el valor a:**
   ```
   bedrock-proxy-dev-alb-258169205.eu-west-1.elb.amazonaws.com
   ```

**4. Guarda los cambios**

**5. Espera a que se propague (5-30 minutos)**

### Verificación

Una vez actualizado, verifica con:

```bash
# Debe resolver al nuevo ALB
dig bedrock-proxy.leancustomer.es

# Debe responder OK
curl https://bedrock-proxy.leancustomer.es/health

# Debe responder HTTP 200
curl -s -o /dev/null -w "%{http_code}" https://bedrock-proxy.leancustomer.es/health
```

## 📋 Resumen de Cambios

| Aspecto | Antiguo | Nuevo |
|---------|---------|-------|
| ALB DNS | bedrock-proxy-dev-alb-961374083.eu-west-1.elb.amazonaws.com | bedrock-proxy-dev-alb-258169205.eu-west-1.elb.amazonaws.com |
| ALB ARN | .../8885d3286b172f89 | .../0a500518f6a64d74 |
| Estado | ❌ Eliminado | ✅ Activo |
| HTTP (80) | ❌ No funciona | ✅ Funciona |
| HTTPS (443) | ❌ No funciona | ✅ Funciona |
| Certificado | bedrock-proxy.leancustomer.es | bedrock-proxy.leancustomer.es |

## 🔧 Configuración del Nuevo ALB

### Listeners
- **Puerto 80 (HTTP)**: Forward a Target Group (puerto 8080)
- **Puerto 443 (HTTPS)**: Forward a Target Group (puerto 8080) con certificado

### Target Group
- **Nombre**: bedrock-proxy-dev-tg
- **Puerto**: 8080
- **Protocolo**: HTTP
- **Targets**: 3 instancias EC2

### Security Group
- **ID**: sg-0500646b3bb268ead
- **Nombre**: bedrock-proxy-dev-alb-sg

## ⏱️ Tiempo de Propagación DNS

- **Inmediato**: Algunos proveedores
- **5-10 minutos**: La mayoría
- **Máximo**: 30 minutos

Si después de 30 minutos aún no funciona, verifica:
1. El registro CNAME está correcto
2. El TTL es bajo (300 segundos o menos)
3. Limpia el caché DNS local: `sudo dscacheutil -flushcache` (macOS)