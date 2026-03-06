"""
Configuration Module
====================
Configuración para la Lambda de autenticación
"""

import os

# Cognito Configuration
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_UaMIbG9pD')
COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID', '15b1ub3navqgh0ushcqo2ngfsk')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-1')

# Database Configuration
DB_SECRET_NAME = os.environ.get('DB_SECRET_NAME', 'identity-mgmt-dev-db-admin')

# JWT Configuration
JWT_SECRET_NAME = os.environ.get('JWT_SECRET_NAME', 'identity-mgmt-dev-login-key-access')
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '1'))

# Application Configuration
APP_NAME = 'auth-lambda'
APP_VERSION = '1.0.0'

# Permission Configuration
# UUID de la aplicación de Identity Management en la tabla identity-manager-applications-tbl
# Este valor se puede sobrescribir con la variable de entorno IDENTITY_MGMT_APP_ID
# o pasando el parámetro app_id en el request de login
IDENTITY_MGMT_APP_ID = os.environ.get('IDENTITY_MGMT_APP_ID', 'e61e1af9-8992-4bdf-be65-9cad86f34da0')
