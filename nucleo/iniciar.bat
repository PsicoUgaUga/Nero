@echo off
title Nero - Agente Autonomo
color 0A
cd /d C:\Nero
echo.
echo ================================================
echo    NERO - Agente Autonomo com Treinador Groq
echo ================================================
echo.
echo   Ctrl+C  - cancela a tarefa atual
echo   ESC     - mata o Nero (panic button)
echo   sair    - sai do Nero
echo.
echo ================================================
echo.
python agente.py
pause