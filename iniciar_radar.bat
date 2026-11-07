@echo off
title Mimozae Deals Hub - @mimozae.of
echo ======================================================
echo    Iniciando Mimozae Deals Hub - Radar de Ofertas
echo    Instagram: @mimozae.of
echo ======================================================
cd /d "%~dp0"
python -m streamlit run app.py
pause
