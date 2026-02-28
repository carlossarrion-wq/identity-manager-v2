# Seguridad de la API - Identity Manager

## ⚠️ PROBLEMA ACTUAL: Sin Autenticación

### Estado Actual
La Lambda Function URL está configurada con **`AuthType = NONE`**, lo que significa:
- ❌ **Cualquiera puede llamar a la API**
- ❌ **No hay autenticación**
- ❌ **No hay autorización**
- ❌ **Cualquiera puede crear tokens JWT**
- ❌ **Cualquiera puede crear/eliminar usuarios**

```hcl
# deployment/terraform/modules/lambda/main.tf
resource "aws_lambda_function_url" "api_url" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"  # ⚠️ SIN AUTENTICACIÓN
}
```

---

## 🔒 Soluciones de Seguridad

### **Opción 1: AWS IAM Authentication (Recomendado para APIs internas)**

#### Ventajas:
- ✅ Autenticación con credenciales AWS
- ✅ Control granular con IAM policies
- ✅ Sin costo adicional
- ✅ Integración nativa con AWS

#### Desventajas:
- ❌ Solo para clientes AWS (no para frontend público)
- ❌ Requiere AWS SDK en el cliente

#### Implementación:

```hcl
# deployment/terraform/modules/lambda/main.tf
resource "aws_lambda_function_url" "api_url" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "AWS_IAM"  # ✅ Requiere autenticación IAM
  
  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type", "authorization"]
  }
}

# Crear rol IAM para clientes
resource "aws_iam_role" "api_client" {
  name = "identity-mgmt-api-client"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::ACCOUNT_ID:user/admin"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy para invocar la Lambda
resource "aws_iam_role_policy" "invoke_lambda" {
  role = aws_iam_role.api_client.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "lambda:InvokeFunctionUrl"
      Resource = aws_lambda_function.api.arn
    }]
  })
}
```

#### Uso desde cliente:

```python
import boto3
import requests
from requests_aws4auth import AWS4Auth

# Obtener credenciales AWS
session = boto3.Session()
credentials = session.get_credentials()

# Crear autenticación AWS SigV4
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    'eu-west-1',
    'lambda',
    session_token=credentials.token
)

# Llamar a la API
response = requests.post(
    'https://vgrajswesgyujgxpw5g65tw5py0kihum.lambda-url.eu-west-1.on.aws/',
    json={'operation': 'create_token', 'data': {...}},
    auth=auth
)
```

---

### **Opción 2: API Gateway + Cognito Authorizer (Recomendado para Frontend)**

#### Ventajas:
- ✅ Autenticación con Cognito User Pool
- ✅ Perfecto para frontend web/móvil
- ✅ Control de acceso por grupos
- ✅ Rate limiting y throttling
- ✅ API Keys opcionales

#### Desventajas:
- ❌ Costo adicional (~$3.50/millón de requests)
- ❌ Más complejo de configurar

#### Arquitectura:

```
Frontend → API Gateway → Cognito Authorizer → Lambda
                ↓
         Valida JWT de Cognito
```

#### Implementación:

```hcl
# deployment/terraform/modules/api_gateway/main.tf

# API Gateway REST API
resource "aws_api_gateway_rest_api" "identity_mgmt" {
  name        = "identity-mgmt-api"
  description = "Identity Manager API with Cognito Auth"
}

# Cognito Authorizer
resource "aws_api_gateway_authorizer" "cognito" {
  name          = "cognito-authorizer"
  rest_api_id   = aws_api_gateway_rest_api.identity_mgmt.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [var.cognito_user_pool_arn]
}

# Resource /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.identity_mgmt.id
  parent_id   = aws_api_gateway_rest_api.identity_mgmt.root_resource_id
  path_part   = "api"
}

# Method POST /api
resource "aws_api_gateway_method" "post" {
  rest_api_id   = aws_api_gateway_rest_api.identity_mgmt.id
  resource_id   = aws_api_gateway_resource.api.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
  
  # Requiere que el usuario esté en el grupo "admins"
  authorization_scopes = ["aws.cognito.signin.user.admin"]
}

# Integration con Lambda
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.identity_mgmt.id
  resource_id = aws_api_gateway_resource.api.id
  http_method = aws_api_gateway_method.post.http_method
  
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}
```

#### Uso desde frontend:

```javascript
// 1. Login con Cognito
const auth = await Auth.signIn(username, password);
const idToken = auth.signInUserSession.idToken.jwtToken;

// 2. Llamar a API Gateway con token
const response = await fetch('https://api.example.com/api', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${idToken}`  // Token de Cognito
  },
  body: JSON.stringify({
    operation: 'create_token',
    data: {...}
  })
});
```

---

### **Opción 3: Custom Authorizer Lambda (Máxima Flexibilidad)**

#### Ventajas:
- ✅ Lógica de autenticación personalizada
- ✅ Validar tokens JWT propios
- ✅ Integración con sistemas externos
- ✅ Control total

#### Desventajas:
- ❌ Más complejo de implementar
- ❌ Costo adicional por invocación del authorizer

#### Implementación:

```python
# authorizer_lambda.py
import jwt
import os

def lambda_handler(event, context):
    """Custom authorizer para validar tokens JWT"""
    
    token = event['headers'].get('Authorization', '').replace('Bearer ', '')
    
    try:
        # Validar token JWT
        secret_key = os.environ['JWT_SECRET_KEY']
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Verificar permisos
        if 'admin' not in payload.get('groups', []):
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Permitir acceso
        return generate_policy(payload['user_id'], 'Allow', event['methodArn'], payload)
        
    except Exception as e:
        return generate_policy('user', 'Deny', event['methodArn'])

def generate_policy(principal_id, effect, resource, context=None):
    """Generar IAM policy"""
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        },
        'context': context or {}
    }
```

---

### **Opción 4: API Key + Rate Limiting (Básico)**

#### Ventajas:
- ✅ Simple de implementar
- ✅ Rate limiting incluido
- ✅ Bajo costo

#### Desventajas:
- ❌ No identifica usuarios
- ❌ API key puede ser compartida
- ❌ Menos seguro

#### Implementación:

```hcl
resource "aws_api_gateway_api_key" "identity_mgmt" {
  name = "identity-mgmt-api-key"
}

resource "aws_api_gateway_usage_plan" "identity_mgmt" {
  name = "identity-mgmt-usage-plan"
  
  api_stages {
    api_id = aws_api_gateway_rest_api.identity_mgmt.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }
  
  throttle_settings {
    burst_limit = 100
    rate_limit  = 50
  }
}
```

---

## 🎯 Recomendación por Caso de Uso

### **Para Desarrollo/Testing:**
```
✅ Opción Actual (NONE)
- Solo para desarrollo local
- NUNCA en producción
```

### **Para API Interna (Backend-to-Backend):**
```
✅ Opción 1: AWS IAM Authentication
- Autenticación con credenciales AWS
- Control granular con IAM
- Sin costo adicional
```

### **Para Frontend Web/Móvil:**
```
✅ Opción 2: API Gateway + Cognito Authorizer
- Usuarios autenticados con Cognito
- Control por grupos
- Rate limiting
```

### **Para Máxima Flexibilidad:**
```
✅ Opción 3: Custom Authorizer
- Lógica personalizada
- Validación de tokens propios
- Integración con sistemas externos
```

---

## 🔐 Implementación Recomendada: Doble Capa de Seguridad

### **Capa 1: API Gateway + Cognito (Frontend)**

```
Frontend → API Gateway → Cognito Authorizer → Lambda
           (Valida JWT de Cognito)
```

### **Capa 2: Validación Interna en Lambda**

```python
def lambda_handler(event, context):
    """Handler con validación adicional"""
    
    # 1. Extraer usuario del contexto de Cognito
    cognito_user = event['requestContext']['authorizer']['claims']
    user_id = cognito_user['sub']
    groups = cognito_user.get('cognito:groups', [])
    
    # 2. Validar permisos según operación
    operation = body.get('operation')
    
    if operation in ['create_user', 'delete_user']:
        if 'admins' not in groups:
            return build_error_response(
                'FORBIDDEN',
                'Solo administradores pueden realizar esta operación',
                403
            )
    
    if operation == 'create_token':
        # Solo puede crear tokens para sí mismo (excepto admins)
        if body['data']['user_id'] != user_id and 'admins' not in groups:
            return build_error_response(
                'FORBIDDEN',
                'Solo puedes crear tokens para tu propio usuario',
                403
            )
    
    # 3. Procesar operación
    return route_operation(operation, body, request_id)
```

---

## 📋 Plan de Implementación

### **Fase 1: Desarrollo (Actual)**
- ✅ Lambda Function URL sin autenticación
- ⚠️ Solo para testing local

### **Fase 2: Testing/Staging**
- [ ] Implementar API Gateway
- [ ] Configurar Cognito Authorizer
- [ ] Añadir validación de permisos en Lambda
- [ ] Configurar rate limiting

### **Fase 3: Producción**
- [ ] Habilitar AWS WAF
- [ ] Configurar CloudWatch Alarms
- [ ] Implementar logging de auditoría
- [ ] Configurar backup y disaster recovery

---

## 🚨 Acciones Inmediatas Recomendadas

1. **Deshabilitar Lambda Function URL pública**
   ```hcl
   # Comentar o eliminar
   # resource "aws_lambda_function_url" "api_url" { ... }
   ```

2. **Implementar API Gateway con Cognito**
   - Crear módulo de API Gateway
   - Configurar Cognito Authorizer
   - Migrar endpoints

3. **Añadir validación de permisos en Lambda**
   - Verificar grupos de Cognito
   - Validar operaciones permitidas
   - Registrar intentos de acceso no autorizado

4. **Configurar monitoreo**
   - CloudWatch Alarms para accesos sospechosos
   - Logs de auditoría
   - Alertas de seguridad

---

## 💰 Costos Estimados

| Opción | Costo Mensual (1M requests) |
|--------|----------------------------|
| Lambda Function URL (NONE) | $0 | ⚠️ INSEGURO
| Lambda Function URL (IAM) | $0 | ✅ Seguro para APIs internas
| API Gateway + Cognito | ~$3.50 | ✅ Seguro para frontend
| Custom Authorizer | ~$4.00 | ✅ Máxima flexibilidad

---

## 📚 Referencias

- [AWS Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
- [API Gateway Cognito Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)
- [AWS IAM Authentication](https://docs.aws.amazon.com/general/latest/gr/signing_aws_api_requests.html)
- [Custom Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
