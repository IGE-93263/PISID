@echo off
echo ============================================
echo  IP deste PC (PC1) para ligar do PC2
echo ============================================
echo.
echo Usa o IP da tua rede local (192.168.x.x):
echo.
ipconfig | findstr /i "IPv4"
echo.
echo No PC2, antes de correr o mongo_to_mysql.py:
echo   PowerShell: $env:MONGO_HOST="IP_AQUI"
echo   CMD:        set MONGO_HOST=IP_AQUI
echo.
pause
