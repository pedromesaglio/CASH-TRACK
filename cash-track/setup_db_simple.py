#!/usr/bin/env python3
"""
Script para configurar PostgreSQL
Ejecutar: python3 setup_db_simple.py
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_database():
    print("=== Configuración de PostgreSQL ===\n")

    # Configuración
    db_name = "cashtrack"
    db_user = "postgres"  # Usuario por defecto de PostgreSQL
    db_password = ""  # Por defecto no tiene contraseña en instalaciones locales

    try:
        # Conectar como postgres sin base de datos específica
        conn = psycopg2.connect(
            host="localhost",
            user=db_user,
            password=db_password,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Verificar si la base de datos ya existe
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if not exists:
            # Crear la base de datos
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_name)
            ))
            print(f"✅ Base de datos '{db_name}' creada exitosamente")
        else:
            print(f"ℹ️  Base de datos '{db_name}' ya existe")

        cursor.close()
        conn.close()

        print("\nConfiguración exitosa:")
        print(f"  Base de datos: {db_name}")
        print(f"  Usuario: {db_user}")
        print(f"  Host: localhost")
        print(f"  Puerto: 5432")
        print("\n✅ PostgreSQL configurado correctamente")

        return True

    except psycopg2.Error as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        print("\nPor favor, ejecuta estos comandos en tu terminal:")
        print(f"  sudo -u postgres createdb {db_name}")
        print("\nO contacta al usuario con permisos de PostgreSQL")
        return False

if __name__ == "__main__":
    setup_database()
