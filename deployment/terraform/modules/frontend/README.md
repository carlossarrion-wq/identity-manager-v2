# Frontend Module - Identity Manager

## Descripción

Módulo de Terraform para desplegar el frontend de Identity Manager en S3 con distribución CloudFront CDN.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                         Usuario                              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CloudFront Distribution                         │
│         (CDN Global con HTTPS y Compresión)                  │
│                                                               │
│  - Default Root: login.html                                  │
│  - Cache: CSS/JS (1 día), HTML (1 hora)                     │
│  - Error Pages: 403/404 → login.html                        │
│  - Compression: Enabled                                      │
│  - Protocol: HTTPS only (redirect HTTP)                      │
└────────────────────────┬────────────────────────────────────┘
                         │ Origin Access Identity (OAI)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    S3 Bucket (Private)                       │
│                                                               │
│  Structure:                                                  │
│  ├── login.html                                              │
│  └── dashboard/                                              │
│      ├── index.html                                          │
│      ├── css/                                                │
│      │   └── dashboard.css                                   │
│      └── js/                                                 │
│          ├── api.js                                          │
│          ├── auth-guard.js                                   │
│          ├── config.js                                       │
│          ├── dashboard.js                                    │
│          ├── jwt-permissions.js                              │
│          ├── permissions.js                                  │
│          ├── proxy-usage.js                                  │
│          └── user-quotas.js                                  │
│                                                               │
│  Security:                                                   │
│  - Block Public Access: Enabled                              │
│  - Encryption: AES256                                        │
│  - Versioning: Enabled                                       │
│  - Access: Only via CloudFront OAI                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Uso

```hcl
module "frontend" {
  source = "../../modules/frontend"

  project_name         = "identity-mgmt"
  environment          = "dev"
  frontend_source_path = "${path.module}/../../../../frontend"
  cloudfront_price_class = "PriceClass_100"

  tags = {
    Environment = "dev"
    Application = "identity-manager"
    Component   = "frontend"
  }
}
```

---

## Variables

### Requeridas

#### `project_name`
- **Descripción:** Nombre del proyecto
- **Tipo:** `string`
- **Ejemplo:** `"identity-mgmt"`
- **Validación:** Lowercase, empieza con letra, solo letras/números/guiones

#### `environment`
- **Descripción:** Entorno de despliegue
- **Tipo:** `string`
- **Valores:** `dev`, `pre`, `pro`

### Opcionales

#### `frontend_source_path`
- **Descripción:** Ruta a los archivos fuente del frontend
- **Tipo:** `string`
- **Default:** `"../../frontend"`
- **Ejemplo:** `"${path.module}/../../../../frontend"`

#### `cloudfront_price_class`
- **Descripción:** Clase de precio de CloudFront
- **Tipo:** `string`
- **Default:** `"PriceClass_100"` (US, Canada, Europe)
- **Opciones:**
  - `PriceClass_100`: US, Canada, Europe
  - `PriceClass_200`: US, Canada, Europe, Asia, Middle East, Africa
  - `PriceClass_All`: Todas las ubicaciones

#### `tags`
- **Descripción:** Tags adicionales para los recursos
- **Tipo:** `map(string)`
- **Default:** `{}`

---

## Outputs

### `s3_bucket_name`
- **Descripción:** Nombre del bucket S3
- **Valor:** `identity-mgmt-dev-frontend-s3`

### `s3_bucket_arn`
- **Descripción:** ARN del bucket S3
- **Valor:** `arn:aws:s3:::identity-mgmt-dev-frontend-s3`

### `cloudfront_distribution_id`
- **Descripción:** ID de la distribución CloudFront
- **Uso:** Para invalidar caché
- **Ejemplo:** `E1234567890ABC`

### `cloudfront_domain_name`
- **Descripción:** Dominio de CloudFront
- **Ejemplo:** `d1234567890abc.cloudfront.net`

### `cloudfront_url`
- **Descripción:** URL completa HTTPS
- **Ejemplo:** `https://d1234567890abc.cloudfront.net`

### `cloudfront_hosted_zone_id`
- **Descripción:** Zone ID de Route 53 para CloudFront
- **Uso:** Para crear alias records

---

## Recursos Creados

### 1. S3 Bucket
```hcl
Resource: aws_s3_bucket.frontend
Name: identity-mgmt-dev-frontend-s3
```

**Configuración:**
- ✅ Versioning habilitado
- ✅ Encryption: AES256
- ✅ Public Access: Bloqueado
- ✅ Access: Solo via CloudFront OAI

### 2. CloudFront Distribution
```hcl
Resource: aws_cloudfront_distribution.frontend
```

**Configuración:**
- ✅ HTTPS only (redirect HTTP)
- ✅ IPv6 habilitado
- ✅ Compression habilitado
- ✅ Default root: login.html
- ✅ Error pages: 403/404 → login.html

**Cache Behaviors:**
```yaml
HTML Files:
  TTL: 0 min - 1 hour - 1 day
  Compress: Yes
  
CSS Files (/dashboard/css/*):
  TTL: 0 min - 1 day - 1 year
  Compress: Yes
  
JS Files (/dashboard/js/*):
  TTL: 0 min - 1 day - 1 year
  Compress: Yes
```

### 3. Origin Access Identity (OAI)
```hcl
Resource: aws_cloudfront_origin_access_identity.frontend
```

**Propósito:** Permitir a CloudFront acceder al bucket S3 privado

### 4. S3 Bucket Policy
```hcl
Resource: aws_s3_bucket_policy.frontend
```

**Permite:** Solo CloudFront OAI puede leer objetos

### 5. S3 Objects
```hcl
Resources:
  - aws_s3_object.login_html
  - aws_s3_object.dashboard_index
  - aws_s3_object.dashboard_css (for_each)
  - aws_s3_object.dashboard_js (for_each)
```

**Auto-upload:** Terraform sube automáticamente todos los archivos

---

## Estructura de Archivos Frontend

```
frontend/
├── login.html                    # Página de login
└── dashboard/
    ├── index.html                # Dashboard principal
    ├── css/
    │   └── dashboard.css         # Estilos
    └── js/
        ├── api.js                # Cliente API
        ├── auth-guard.js         # Protección de rutas
        ├── config.js             # Configuración
        ├── dashboard.js          # Lógica principal
        ├── jwt-permissions.js    # Manejo de permisos JWT
        ├── permissions.js        # Gestión de permisos
        ├── proxy-usage.js        # Analytics de uso
        └── user-quotas.js        # Gestión de cuotas
```

---

## Configuración del Frontend

### config.js
```javascript
const API_CONFIG = {
    BASE_URL: 'https://flzqvv3jt4.execute-api.eu-west-1.amazonaws.com/dev',
    COGNITO: {
        USER_POOL_ID: 'eu-west-1_UaMIbG9pD',
        CLIENT_ID: 'xxx',
        REGION: 'eu-west-1'
    }
};
```

**⚠️ IMPORTANTE:** Actualizar `config.js` con los valores correctos antes del despliegue.

---

## Despliegue

### Opción 1: Terraform Apply
```bash
cd deployment/terraform/environments/dev

# Aplicar cambios
terraform apply

# Outputs
terraform output cloudfront_url
```

### Opción 2: Actualizar Solo Frontend
```bash
# 1. Modificar archivos en /frontend

# 2. Aplicar solo el módulo frontend
terraform apply -target=module.frontend

# 3. Invalidar caché de CloudFront
aws cloudfront create-invalidation \
  --distribution-id $(terraform output -raw frontend_cloudfront_distribution_id) \
  --paths "/*"
```

---

## Invalidación de Caché

### Invalidar Todo
```bash
DISTRIBUTION_ID=$(terraform output -raw frontend_cloudfront_distribution_id)

aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

### Invalidar Archivos Específicos
```bash
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/dashboard/js/config.js" "/dashboard/index.html"
```

### Verificar Invalidación
```bash
aws cloudfront get-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --id <invalidation-id>
```

---

## Seguridad

### 1. S3 Bucket
```yaml
✅ Block Public Access: Enabled
✅ Encryption: AES256 (server-side)
✅ Versioning: Enabled
✅ Access: Only via CloudFront OAI
✅ No public URLs
```

### 2. CloudFront
```yaml
✅ HTTPS Only: HTTP redirects to HTTPS
✅ TLS: Minimum TLSv1.2_2021
✅ Origin: Private S3 via OAI
✅ No custom domain (using CloudFront domain)
```

### 3. Frontend Code
```yaml
✅ JWT Tokens: Stored in sessionStorage (not localStorage)
✅ Auth Guard: Protege rutas del dashboard
✅ CORS: Configurado en API Gateway
✅ No credentials in code: Config via config.js
```

---

## Troubleshooting

### Error: 403 Forbidden
**Causa:** CloudFront no puede acceder a S3

**Solución:**
```bash
# Verificar bucket policy
aws s3api get-bucket-policy --bucket identity-mgmt-dev-frontend-s3

# Verificar OAI
aws cloudfront get-cloud-front-origin-access-identity \
  --id $(terraform output -raw cloudfront_oai_id)
```

### Error: 404 Not Found
**Causa:** Archivo no existe en S3

**Solución:**
```bash
# Listar archivos en S3
aws s3 ls s3://identity-mgmt-dev-frontend-s3/ --recursive

# Re-aplicar Terraform para subir archivos
terraform apply -target=module.frontend
```

### Caché No Se Actualiza
**Causa:** CloudFront está sirviendo versión cacheada

**Solución:**
```bash
# Invalidar caché
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"

# O esperar TTL (1 hora para HTML, 1 día para CSS/JS)
```

### Error: CORS
**Causa:** API Gateway no tiene CORS configurado

**Solución:**
1. Verificar headers CORS en Lambda (response_builder.py)
2. Verificar métodos OPTIONS en API Gateway
3. Verificar que API Gateway devuelve headers CORS

---

## Performance

### Cache TTL
```yaml
HTML Files:
  Default: 1 hour
  Max: 1 day
  
CSS/JS Files:
  Default: 1 day
  Max: 1 year
  
Compression: Enabled (gzip/brotli)
```

### CloudFront Locations
```yaml
PriceClass_100:
  - North America
  - Europe
  
PriceClass_200:
  - North America
  - Europe
  - Asia
  - Middle East
  - Africa
  
PriceClass_All:
  - All CloudFront edge locations
```

---

## Costos Estimados

### S3
```
Storage: ~1 MB
Requests: ~1000/month
Cost: < $0.10/month
```

### CloudFront
```
Data Transfer: ~10 GB/month
Requests: ~10,000/month
Cost: ~$1-2/month (PriceClass_100)
```

**Total:** ~$2-3/month

---

## Ejemplos

### Despliegue Completo
```hcl
module "frontend" {
  source = "../../modules/frontend"

  project_name         = "identity-mgmt"
  environment          = "dev"
  frontend_source_path = "${path.module}/../../../../frontend"
  cloudfront_price_class = "PriceClass_100"

  tags = {
    Environment = "dev"
    Application = "identity-manager"
    Component   = "frontend"
    Team        = "Platform"
    CostCenter  = "Engineering"
  }
}

output "frontend_url" {
  value = module.frontend.cloudfront_url
}
```

### Actualizar Config.js
```javascript
// frontend/dashboard/js/config.js
const API_CONFIG = {
    BASE_URL: 'https://flzqvv3jt4.execute-api.eu-west-1.amazonaws.com/dev',
    COGNITO: {
        USER_POOL_ID: 'eu-west-1_UaMIbG9pD',
        CLIENT_ID: '7abc123def456ghi789jkl',
        REGION: 'eu-west-1'
    }
};
```

---

## Changelog

### 2026-03-10
- ✅ Documentación completa creada
- ✅ Ejemplos de uso añadidos
- ✅ Troubleshooting guide
- ✅ Security best practices

### 2026-03-03
- ✅ Versión inicial del módulo
- ✅ S3 + CloudFront configurado
- ✅ Auto-upload de archivos
- ✅ Cache behaviors optimizados

---

## Soporte

**Documentación:**
- `/deployment/terraform/DEPLOYMENT_SUMMARY.md`
- `/deployment/terraform/MANUAL_CHANGES_APPLIED.md`

**Contacto:**
- Equipo de Platform Engineering