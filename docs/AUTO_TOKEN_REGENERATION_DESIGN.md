# Auto Token Regeneration Feature - High Level Design

## 📋 Overview

Feature que permite la regeneración automática de tokens JWT expirados para usuarios que tienen habilitada esta funcionalidad mediante un custom field.

## 🎯 Objetivo

Mejorar la experiencia de usuario permitiendo que tokens expirados se regeneren automáticamente sin intervención manual, enviando el nuevo token por email.

## 🔑 Componentes Principales

### 1. Custom Field en Cognito

**Ubicación:** AWS Cognito User Pool - Custom Attributes

**Atributo personalizado:**
```
custom:auto_regen_tokens (String: "true" | "false")
```

**Propósito:** Flag que indica si el usuario tiene habilitada la regeneración automática de tokens.

**Configuración en Cognito:**
- Tipo: String (Cognito no soporta Boolean nativamente)
- Mutable: Sí (el usuario puede cambiar este valor)
- Valores válidos: "true" o "false"
- Valor por defecto: "false"

### 2. Flujo de Detección y Regeneración

#### 2.1 Punto de Interceptación
**Ubicación:** `proxy-bedrock/pkg/auth/middleware.go`

**Momento:** Cuando `ValidateToken()` falla con error de expiración

**Condiciones para activar regeneración:**
1. ✅ Token es auténtico (firma válida)
2. ✅ Token está expirado (no revocado, no inválido)
3. ✅ Usuario tiene `custom:auto_regen_tokens = true` en Cognito
4. ✅ Token existe en la base de datos
5. ✅ Usuario no excede el límite máximo de tokens activos
6. ✅ No se excede el límite de regeneraciones diarias (3/día)

#### 2.2 Proceso de Validación
```
┌─────────────────────────────────────────────────────────────┐
│ 1. Recibir petición con token                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ValidateToken() → Error: "token expired"                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DecodeTokenUnsafe() → Extraer claims                     │
│    - user_id, email, team, person, profile                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Verificar en BD:                                          │
│    - Token existe y no está revocado                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Consultar Cognito:                                        │
│    - Obtener atributo custom:auto_regen_tokens              │
│    - Verificar si es "true"                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─── NO → Retornar 401 (token_expired)
                     │
                     └─── SÍ → Continuar regeneración
                              │
                              ▼
                     ┌────────────────────────────────────┐
                     │ 6. Llamar a Lambda API:            │
                     │    POST /api/tokens/regenerate     │
                     │    - expired_token_jti             │
                     │    - user_id                       │
                     └────────┬───────────────────────────┘
                              │
                              ▼
                     ┌────────────────────────────────────┐
                     │ 7. Lambda genera nuevo token:      │
                     │    - Mismo profile                 │
                     │    - Mismo team                    │
                     │    - Misma duración                │
                     │    - Nuevo JTI                     │
                     └────────┬───────────────────────────┘
                              │
                              ▼
                     ┌────────────────────────────────────┐
                     │ 8. Guardar en BD                   │
                     │    - Insertar nuevo token          │
                     │    - Marcar token viejo como       │
                     │      "regenerated"                 │
                     └────────┬───────────────────────────┘
                              │
                              ▼
                     ┌────────────────────────────────────┐
                     │ 9. Enviar email con nuevo token    │
                     └────────┬───────────────────────────┘
                              │
                              ▼
                     ┌────────────────────────────────────┐
                     │ 10. Retornar 401 con mensaje       │
                     │     especial indicando que se      │
                     │     envió nuevo token por email    │
                     └────────────────────────────────────┘
```

### 3. Cambios en Base de Datos

#### 3.1 Tabla `identity-manager-tokens-tbl`
```sql
-- Añadir campo para rastrear regeneraciones
ALTER TABLE "identity-manager-tokens-tbl"
ADD COLUMN IF NOT EXISTS regenerated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS regenerated_to_jti UUID;

-- Índice para tokens regenerados
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated 
ON "identity-manager-tokens-tbl" (regenerated_at)
WHERE regenerated_at IS NOT NULL;
```

### 4. Cambios en Código

#### 4.1 Proxy Bedrock (`pkg/auth/middleware.go`)

**Nueva función:**
```go
func (am *AuthMiddleware) handleExpiredToken(
    r *http.Request,
    tokenString string,
    claims *JWTClaims,
) (shouldRegenerate bool, err error)
```

**Lógica:**
1. Verificar que el token existe en BD y no está revocado
2. **Consultar Cognito** para obtener el atributo `custom:auto_regen_tokens` del usuario
3. Si el valor es "true", llamar a API Lambda para regenerar
4. Retornar respuesta especial al cliente

**Integración con Cognito:**
```go
// El proxy necesitará hacer una llamada a Cognito para obtener el custom attribute
// Esto se puede hacer mediante:
// 1. AWS SDK for Go (Cognito Identity Provider)
// 2. Llamada HTTP a la Lambda API que consulte Cognito
// 
// Opción recomendada: Llamar a Lambda API que ya tiene integración con Cognito
```

#### 4.2 Identity Manager API Lambda

**Nuevo endpoint:**
```
POST /api/tokens/regenerate
```

**Request:**
```json
{
  "expired_token_jti": "uuid-del-token-expirado",
  "user_id": "uuid-del-usuario",
  "reason": "auto_regeneration"
}
```

**Response:**
```json
{
  "success": true,
  "message": "New token generated and sent via email",
  "new_token_jti": "uuid-del-nuevo-token",
  "email_sent": true
}
```

**Nuevo servicio:** `token_regeneration_service.py`
```python
class TokenRegenerationService:
    def regenerate_expired_token(
        self,
        expired_token_jti: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Regenera un token expirado con las mismas características
        """
        # 1. Obtener token expirado de BD
        # 2. Verificar que usuario tiene auto_regen habilitado
        # 3. Obtener profile_id del token expirado
        # 4. Generar nuevo token con mismo profile
        # 5. Marcar token viejo como regenerado
        # 6. Enviar email con nuevo token
        # 7. Registrar evento en logs
```

### 5. Respuestas HTTP

#### 5.1 Token Expirado SIN Auto-Regeneración
```json
HTTP 401 Unauthorized
{
  "error": {
    "type": "token_expired",
    "message": "Token has expired",
    "code": 401
  }
}
```

#### 5.2 Token Expirado CON Auto-Regeneración Exitosa
```json
HTTP 401 Unauthorized
{
  "error": {
    "type": "token_expired_regenerated",
    "message": "Token has expired. A new token has been generated and sent to your email",
    "code": 401,
    "auto_regenerated": true,
    "email_sent": true
  }
}
```

#### 5.3 Token Expirado CON Auto-Regeneración Fallida
```json
HTTP 401 Unauthorized
{
  "error": {
    "type": "token_expired_regen_failed",
    "message": "Token has expired. Auto-regeneration failed. Please create a new token manually",
    "code": 401,
    "auto_regenerated": false,
    "regeneration_error": "Failed to send email"
  }
}
```

#### 5.4 Token Expirado - Límite de Tokens Activos Excedido
```json
HTTP 401 Unauthorized
{
  "error": {
    "type": "token_expired_max_tokens",
    "message": "Token has expired. Cannot auto-regenerate: maximum number of active tokens reached. Please revoke old tokens in the dashboard",
    "code": 401,
    "auto_regenerated": false,
    "active_tokens_count": 5,
    "max_tokens_allowed": 5,
    "action_required": "revoke_old_tokens"
  }
}
```

### 6. Email Template

**Asunto:** "🔄 Token JWT Regenerado Automáticamente - Identity Manager"

**Contenido:**
- Indicar que el token anterior expiró
- Mostrar fecha de expiración del token anterior
- Proporcionar el nuevo token
- Indicar que tiene la misma configuración (profile, team, duración)
- Recordar que puede desactivar esta función en el dashboard

### 7. Seguridad y Límites

#### 7.1 Rate Limiting
- **Máximo 3 regeneraciones por usuario por día**
- Prevenir abuso del sistema
- Registrar intentos en tabla de auditoría

#### 7.2 Validaciones
- ✅ Token debe ser auténtico (firma válida)
- ✅ Token debe estar expirado (no revocado)
- ✅ Usuario debe existir y estar activo en Cognito
- ✅ Usuario debe tener `custom:auto_regen_tokens = true` en Cognito
- ✅ **Usuario no debe exceder el límite máximo de tokens activos**
- ✅ No exceder límite de regeneraciones diarias (3/día)

**Validación de Límite de Tokens Activos:**
```python
# En token_regeneration_service.py
def check_active_tokens_limit(self, user_id: str) -> bool:
    """
    Verifica que el usuario no exceda el límite de tokens activos
    
    Returns:
        True si puede crear un nuevo token, False si excede el límite
    """
    # Contar tokens activos (no revocados, no expirados)
    active_tokens_count = self.db.count_active_tokens(user_id)
    
    # Obtener límite máximo del usuario (por defecto 5)
    max_tokens = self.get_user_max_tokens(user_id)  # Default: 5
    
    return active_tokens_count < max_tokens
```

**Comportamiento cuando se excede el límite:**
- Si el usuario ya tiene el máximo de tokens activos, la regeneración automática **NO se ejecuta**
- Se retorna un error específico indicando que debe revocar tokens antiguos
- El usuario debe ir al dashboard y revocar tokens manualmente antes de poder regenerar

#### 7.3 Auditoría
Nueva tabla: `identity-manager-token-regenerations-tbl`
```sql
CREATE TABLE "identity-manager-token-regenerations-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    old_token_jti UUID NOT NULL,
    new_token_jti UUID NOT NULL,
    regeneration_reason VARCHAR(100),
    client_ip VARCHAR(45),
    user_agent TEXT,
    email_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES "identity-manager-users-tbl"(id)
);

CREATE INDEX idx_regen_user_date 
ON "identity-manager-token-regenerations-tbl" (user_id, created_at);
```

### 8. Dashboard UI

#### 8.1 Configuración de Usuario
**Ubicación:** Perfil de usuario

**Toggle:**
```
☐ Auto-regenerar tokens expirados
  Cuando esta opción está activada, si tu token expira,
  el sistema generará automáticamente uno nuevo y te lo
  enviará por email (máximo 3 veces al día).
```

#### 8.2 Historial de Regeneraciones
**Nueva sección en dashboard:**
- Mostrar últimas regeneraciones automáticas
- Fecha y hora
- Token anterior (últimos 8 caracteres)
- Token nuevo (últimos 8 caracteres)
- Estado del email

### 9. Logs y Monitoreo

#### 9.1 Eventos a Registrar
```json
{
  "event.name": "TOKEN_AUTO_REGENERATION",
  "user.id": "uuid",
  "user.email": "email",
  "old_token.jti": "uuid",
  "new_token.jti": "uuid",
  "regeneration.success": true,
  "email.sent": true,
  "client.ip": "ip",
  "timestamp": "iso8601"
}
```

#### 9.2 Métricas CloudWatch
- Número de regeneraciones por día
- Tasa de éxito de regeneraciones
- Tasa de éxito de envío de emails
- Usuarios con auto-regeneración habilitada

### 10. Casos de Uso

#### Caso 1: Usuario con Auto-Regen Habilitado
```
Usuario → Petición con token expirado
       → Proxy detecta expiración
       → Verifica auto_regen = true
       → Genera nuevo token
       → Envía email
       → Retorna 401 con mensaje especial
Usuario → Revisa email
       → Copia nuevo token
       → Continúa trabajando
```

#### Caso 2: Usuario sin Auto-Regen
```
Usuario → Petición con token expirado
       → Proxy detecta expiración
       → Verifica auto_regen = false
       → Retorna 401 estándar
Usuario → Va al dashboard
       → Crea nuevo token manualmente
```

#### Caso 3: Límite Diario Excedido
```
Usuario → Petición con token expirado (4ta vez en el día)
       → Proxy detecta expiración
       → Verifica auto_regen = true
       → Verifica límite diario → EXCEDIDO
       → Retorna 401 con mensaje de límite excedido
Usuario → Debe crear token manualmente
```

#### Caso 4: Límite de Tokens Activos Excedido
```
Usuario → Petición con token expirado
       → Proxy detecta expiración
       → Verifica auto_regen = true
       → Lambda verifica tokens activos → 5/5 (MÁXIMO)
       → Retorna 401 con mensaje de tokens máximos
Usuario → Va al dashboard
       → Revoca tokens antiguos
       → Intenta de nuevo (automático o manual)
```

## 📊 Impacto y Beneficios

### Beneficios
✅ Mejor experiencia de usuario
✅ Menos interrupciones en el trabajo
✅ Reducción de tickets de soporte
✅ Automatización de tarea repetitiva

### Consideraciones
⚠️ Posible abuso si no hay rate limiting
⚠️ Dependencia del servicio de email
⚠️ Complejidad adicional en el código
⚠️ Necesidad de monitoreo adicional

## 🚀 Plan de Implementación

### Fase 1: Cognito y Base de Datos (1 día)
- [ ] Añadir custom attribute `custom:auto_regen_tokens` en Cognito User Pool
- [ ] Crear migración para tabla de auditoría `identity-manager-token-regenerations-tbl`
- [ ] Añadir campos `regenerated_at` y `regenerated_to_jti` a tabla de tokens
- [ ] Añadir índices necesarios
- [ ] Probar migraciones

### Fase 2: Backend Lambda (2 días)
- [ ] Crear `token_regeneration_service.py`
- [ ] Añadir método para consultar custom attribute de Cognito
- [ ] Añadir endpoint `/api/tokens/regenerate`
- [ ] Implementar validaciones y rate limiting (3 regeneraciones/día)
- [ ] Crear template de email para token regenerado
- [ ] Tests unitarios

### Fase 3: Proxy Bedrock (2 días)
- [ ] Modificar `middleware.go` para detectar tokens expirados
- [ ] Añadir función `handleExpiredToken()`
- [ ] Integrar llamada HTTP a Lambda API para verificar custom attribute
- [ ] Integrar llamada a endpoint `/api/tokens/regenerate`
- [ ] Añadir logs y métricas específicas
- [ ] Tests de integración

### Fase 4: Dashboard UI (1 día)
- [ ] Añadir toggle en perfil de usuario para activar/desactivar auto-regeneración
- [ ] Integrar con Cognito para actualizar custom attribute
- [ ] Crear sección de historial de regeneraciones
- [ ] Actualizar API calls
- [ ] Tests E2E

### Fase 5: Testing y Despliegue (1 día)
- [ ] Tests de integración completos (Proxy + Lambda + Cognito)
- [ ] Pruebas de carga y rate limiting
- [ ] Documentación de usuario
- [ ] Despliegue a dev
- [ ] Validación en dev
- [ ] Despliegue a producción

**Tiempo total estimado:** 7 días

## 📝 Notas Adicionales

- Esta feature es **opt-in**: usuarios deben activarla explícitamente
- El límite de 3 regeneraciones/día es configurable
- Los tokens regenerados tienen la misma duración que el original
- Se mantiene trazabilidad completa en auditoría
- Compatible con el sistema de cuotas existente