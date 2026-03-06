@echo off
title ErpMovil - Dev Server

echo ============================================
echo   ErpMovil - Iniciando entorno de desarrollo
echo ============================================
echo.

:: Matar procesos previos
echo [1/3] Liberando puertos anteriores...
taskkill /F /IM node.exe /T >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Iniciar Backend
echo [2/3] Iniciando Backend (FastAPI)  ^> http://localhost:8000
start "ErpMovil - Backend" cmd /k "cd /d %~dp0 && python -m uvicorn main:app --reload --port 8000"

:: Esperar 2 segundos para que el backend arranque primero
timeout /t 2 /nobreak >nul

:: Iniciar Frontend
echo [3/3] Iniciando Frontend (Vite)    ^> http://localhost:5173
start "ErpMovil - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --port 5173"

echo.
echo ============================================
echo   Backend  : http://localhost:8000
echo   Docs API : http://localhost:8000/docs
echo   Frontend : http://localhost:5173
echo ============================================
echo.
echo Cierra las ventanas de Backend y Frontend para detener.
