@echo off
echo A parar contentores...
docker-compose down
echo A apagar dados MySQL...
rmdir /s /q mysql_data
mkdir mysql_data
echo A reiniciar MySQL + PHP...
docker-compose up -d
echo Feito. Aguarda ~30s para o MySQL inicializar.
echo Depois corre o patch_grupo32.sql no phpMyAdmin (localhost:9001)
