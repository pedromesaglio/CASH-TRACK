#!/bin/bash
# Script para configurar PostgreSQL para Cash Track

echo "Configurando PostgreSQL..."

# Crear usuario pedro si no existe
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'pedro'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER pedro WITH PASSWORD 'cashtrack2026';"

# Dar permisos
sudo -u postgres psql -c "ALTER USER pedro CREATEDB;"

# Crear base de datos
sudo -u postgres psql -c "DROP DATABASE IF EXISTS cashtrack;"
sudo -u postgres psql -c "CREATE DATABASE cashtrack OWNER pedro;"

echo "✅ PostgreSQL configurado correctamente"
