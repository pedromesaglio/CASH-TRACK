#!/bin/bash

# Script para configurar PostgreSQL para Cash Track
# Ejecutar con: bash setup_postgres.sh

echo "=== Configuración de PostgreSQL para Cash Track ==="
echo ""

# Configuración
DB_NAME="cashtrack"
DB_USER="pedro"
DB_PASSWORD="cashtrack2026"  # Cambiar esta contraseña

echo "Base de datos: $DB_NAME"
echo "Usuario: $DB_USER"
echo ""

# Crear usuario y base de datos
echo "Creando usuario y base de datos en PostgreSQL..."

sudo -u postgres psql << EOF
-- Crear usuario si no existe
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
   END IF;
END
\$\$;

-- Crear base de datos si no existe
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Otorgar permisos
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Conectar a la base de datos y otorgar permisos al esquema
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo ""
echo "✅ Base de datos y usuario creados exitosamente"
echo ""
echo "Configuración:"
echo "  Base de datos: $DB_NAME"
echo "  Usuario: $DB_USER"
echo "  Contraseña: $DB_PASSWORD"
echo "  Host: localhost"
echo "  Puerto: 5432"
echo ""
echo "Copia estos valores al archivo .env"
