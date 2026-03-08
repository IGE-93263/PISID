@echo off
echo 1. A parar todos os contentores...
docker-compose down

echo.
echo 2. A limpar a pasta mysql_data...
:: O rmdir apaga a pasta e tudo o que esta la dentro. O mkdir volta a cria-la vazia.
rmdir /s /q .\mysql_data
mkdir .\mysql_data

echo.
echo 3. A iniciar os contentores de novo...
docker-compose up -d

echo.
echo Feito! A base de dados foi recriada do zero com o ficheiro labirinto.sql.