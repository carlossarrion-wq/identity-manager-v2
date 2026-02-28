"""
Email Service
=============
Servicio para envío de emails usando Gmail SMTP
"""

import boto3
import json
import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime
import pytz

logger = logging.getLogger()


class EmailService:
    """Servicio para envío de emails con Gmail SMTP"""
    
    def __init__(self):
        """Inicializar servicio de email con credenciales de Secrets Manager"""
        self.secrets_client = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
        self.credentials = self._load_credentials()
        
        # SMTP configuration
        self.smtp_config = self.credentials.get('gmail_smtp', {})
        self.email_settings = self.credentials.get('email_settings', {})
        
        self.smtp_server = self.smtp_config.get('server', 'smtp.gmail.com')
        self.smtp_port = self.smtp_config.get('port', 587)
        self.gmail_user = self.smtp_config.get('user', '')
        self.gmail_password = self.smtp_config.get('password', '')
        self.use_tls = self.smtp_config.get('use_tls', True)
        
        # Email settings
        self.timezone = self.email_settings.get('timezone', 'Europe/Madrid')
        self.reply_to = self.email_settings.get('reply_to', self.gmail_user)
        
        logger.info(f"Email service initialized with user: {self.gmail_user}")
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Cargar credenciales desde Secrets Manager"""
        try:
            secret_name = os.environ.get('EMAIL_SMTP_SECRET_NAME')
            
            if not secret_name:
                logger.error("EMAIL_SMTP_SECRET_NAME environment variable not set")
                return {}
            
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            secret_string = response['SecretString']
            credentials = json.loads(secret_string)
            
            logger.info(f"Credentials loaded successfully from secret: {secret_name}")
            return credentials
            
        except Exception as e:
            logger.error(f"Error loading credentials from Secrets Manager: {e}")
            return {}
    
    def _get_madrid_time(self) -> str:
        """Obtener hora actual en zona horaria de Madrid"""
        try:
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
            return now.strftime('%d/%m/%Y %H:%M:%S %Z')
        except Exception:
            return datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    def send_token_email(
        self,
        recipient_email: str,
        recipient_name: str,
        token: str,
        token_info: Dict[str, Any]
    ) -> bool:
        """
        Enviar email con el token JWT creado
        
        Args:
            recipient_email: Email del destinatario
            recipient_name: Nombre del destinatario
            token: Token JWT generado
            token_info: Información adicional del token (expires_at, profile, etc.)
            
        Returns:
            True si el email se envió correctamente
        """
        try:
            # Crear mensaje
            message = MIMEMultipart('alternative')
            message['Subject'] = "🔑 Nuevo Token JWT Creado - Identity Manager"
            message['From'] = f"Identity Manager <{self.gmail_user}>"
            message['To'] = recipient_email
            message['Reply-To'] = self.reply_to
            
            # Construir el cuerpo del email
            text_body = self._build_token_email_text(
                recipient_name=recipient_name,
                token=token,
                token_info=token_info
            )
            
            html_body = self._build_token_email_html(
                recipient_name=recipient_name,
                token=token,
                token_info=token_info
            )
            
            # Adjuntar partes del mensaje
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            
            message.attach(part1)
            message.attach(part2)
            
            # Enviar email via SMTP
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                
                server.login(self.gmail_user, self.gmail_password)
                server.send_message(message)
            
            logger.info(f"Email enviado exitosamente a {recipient_email}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"Error SMTP enviando email a {recipient_email}: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Error inesperado enviando email: {e}")
            return False
    
    def _build_token_email_html(
        self,
        recipient_name: str,
        token: str,
        token_info: Dict[str, Any]
    ) -> str:
        """Construir el cuerpo del email en HTML"""
        
        profile = token_info.get('profile', {})
        expires_at = token_info.get('expires_at', 'N/A')
        validity_days = token_info.get('validity_days', 'N/A')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 0 0 5px 5px;
        }}
        .token-box {{
            background-color: #fff;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            word-wrap: break-word;
            font-family: monospace;
            font-size: 12px;
        }}
        .info-table {{
            width: 100%;
            margin: 20px 0;
        }}
        .info-table td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        .info-table td:first-child {{
            font-weight: bold;
            width: 40%;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔑 Nuevo Token JWT Creado</h1>
    </div>
    <div class="content">
        <p>Hola <strong>{recipient_name}</strong>,</p>
        
        <p>Se ha creado un nuevo token JWT para tu cuenta. A continuación encontrarás los detalles:</p>
        
        <table class="info-table">
            <tr>
                <td>Perfil:</td>
                <td>{profile.get('profile_name', 'N/A')}</td>
            </tr>
            <tr>
                <td>Modelo:</td>
                <td>{profile.get('model', 'N/A')}</td>
            </tr>
            <tr>
                <td>Aplicación:</td>
                <td>{profile.get('application', 'N/A')}</td>
            </tr>
            <tr>
                <td>Validez:</td>
                <td>{validity_days} días</td>
            </tr>
            <tr>
                <td>Expira:</td>
                <td>{expires_at}</td>
            </tr>
        </table>
        
        <p><strong>Tu Token JWT:</strong></p>
        <div class="token-box">
            {token}
        </div>
        
        <div class="warning">
            <strong>⚠️ Importante:</strong>
            <ul>
                <li>Guarda este token en un lugar seguro</li>
                <li>No compartas este token con nadie</li>
                <li>Este email es la única vez que verás el token completo</li>
                <li>Si pierdes el token, deberás crear uno nuevo</li>
            </ul>
        </div>
        
        <p>Si no solicitaste este token, por favor contacta al administrador del sistema inmediatamente.</p>
    </div>
    <div class="footer">
        <p>Este es un email automático, por favor no respondas a este mensaje.</p>
        <p>Enviado desde: {self.gmail_user}</p>
        <p>Fecha y hora: {self._get_madrid_time()}</p>
        <p>&copy; 2026 Identity Manager - Todos los derechos reservados</p>
    </div>
</body>
</html>
"""
        return html
    
    def _build_token_email_text(
        self,
        recipient_name: str,
        token: str,
        token_info: Dict[str, Any]
    ) -> str:
        """Construir el cuerpo del email en texto plano"""
        
        profile = token_info.get('profile', {})
        expires_at = token_info.get('expires_at', 'N/A')
        validity_days = token_info.get('validity_days', 'N/A')
        
        text = f"""
NUEVO TOKEN JWT CREADO
======================

Hola {recipient_name},

Se ha creado un nuevo token JWT para tu cuenta.

DETALLES DEL TOKEN:
-------------------
Perfil: {profile.get('profile_name', 'N/A')}
Modelo: {profile.get('model', 'N/A')}
Aplicación: {profile.get('application', 'N/A')}
Validez: {validity_days} días
Expira: {expires_at}

TU TOKEN JWT:
-------------
{token}

IMPORTANTE:
-----------
* Guarda este token en un lugar seguro
* No compartas este token con nadie
* Este email es la única vez que verás el token completo
* Si pierdes el token, deberás crear uno nuevo

Si no solicitaste este token, por favor contacta al administrador del sistema inmediatamente.

---
Este es un email automático, por favor no respondas a este mensaje.
Enviado desde: {self.gmail_user}
Fecha y hora: {self._get_madrid_time()}
© 2026 Identity Manager - Todos los derechos reservados
"""
        return text
