@echo off
echo ========================================
echo   Iniciando Servidor de Desarrollo
echo ========================================
echo.
echo Servidor corriendo en: http://localhost:8000
echo.
echo Rutas disponibles:
echo   - Login: http://localhost:8000/frontend/login.html
echo   - Dashboard: http://localhost:8000/identity-manager-v2/frontend/dashboard/index.html
echo.
echo Presiona Ctrl+C para detener el servidor
echo ========================================
echo.

python -m http.server 8000