#!/bin/bash

# Script de migración a PostgreSQL
# Ejecuta este script para migrar de SQLite a PostgreSQL

echo "=== Migración de Cash Track a PostgreSQL ==="
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verificar que PostgreSQL esté corriendo
echo -e "${BLUE}1. Verificando PostgreSQL...${NC}"
if ! systemctl is-active --quiet postgresql; then
    echo -e "${RED}PostgreSQL no está corriendo. Iniciando...${NC}"
    sudo systemctl start postgresql
fi
echo -e "${GREEN}✓ PostgreSQL está corriendo${NC}"
echo ""

# 2. Crear usuario PostgreSQL si no existe
echo -e "${BLUE}2. Creando usuario PostgreSQL 'pedro'...${NC}"
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='pedro'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER pedro WITH PASSWORD 'cashtrack2026';"
sudo -u postgres psql -c "ALTER USER pedro CREATEDB;"
echo -e "${GREEN}✓ Usuario PostgreSQL creado/verificado${NC}"
echo ""

# 3. Crear la base de datos
echo -e "${BLUE}3. Creando base de datos 'cashtrack'...${NC}"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS cashtrack;"
sudo -u postgres psql -c "CREATE DATABASE cashtrack OWNER pedro;"
echo -e "${GREEN}✓ Base de datos creada${NC}"
echo ""

# 4. Ejecutar migración
echo -e "${BLUE}4. Migrando datos de SQLite a PostgreSQL...${NC}"
cd /home/pedro/Desktop/cash\ track/cash-track
python3 migrate_to_postgres.py
echo ""

# 5. Actualizar .env
echo -e "${BLUE}5. Actualizando configuración (.env)...${NC}"
sed -i 's/DB_TYPE=sqlite/DB_TYPE=postgresql/' .env
echo -e "${GREEN}✓ Configuración actualizada${NC}"
echo ""

# 6. Crear backup de SQLite
echo -e "${BLUE}6. Creando backup de SQLite...${NC}"
BACKUP_NAME="cashtrack_backup_$(date +%Y%m%d_%H%M%S).db"
cp cashtrack.db "$BACKUP_NAME"
echo -e "${GREEN}✓ Backup creado: $BACKUP_NAME${NC}"
echo ""

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}¡Migración completada!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "Próximos pasos:"
echo "1. Reinicia el servidor"
echo "2. Verifica que todo funcione correctamente"
echo "3. El backup de SQLite está en: $BACKUP_NAME"
