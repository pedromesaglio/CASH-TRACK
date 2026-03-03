#!/usr/bin/env python3
"""
Setup completo de PostgreSQL para Cash Track
Este script configura todo lo necesario para migrar a PostgreSQL
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description, check=True):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")

    try:
        if isinstance(cmd, list):
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)

        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"⚠️  {result.stderr}")

        if result.returncode == 0:
            print(f"✅ {description} - COMPLETADO")
        else:
            print(f"⚠️  {description} - CON ADVERTENCIAS")

        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if not check:
            return False
        sys.exit(1)

def main():
    print("\n" + "="*60)
    print("🚀 SETUP DE POSTGRESQL PARA CASH TRACK")
    print("="*60)

    # Cambiar al directorio correcto
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 1. Verificar PostgreSQL
    print("\n1️⃣  Verificando PostgreSQL...")
    result = subprocess.run(['systemctl', 'is-active', 'postgresql'],
                          capture_output=True, text=True)

    if result.stdout.strip() != 'active':
        print("❌ PostgreSQL no está activo")
        print("Por favor ejecuta: sudo systemctl start postgresql")
        sys.exit(1)
    print("✅ PostgreSQL está corriendo")

    # 2. Crear usuario PostgreSQL (necesita sudo)
    print("\n2️⃣  Configurando usuario PostgreSQL...")
    print("⚠️  Este paso requiere permisos de sudo")
    print("Por favor ejecuta estos comandos manualmente:")
    print("\n" + "="*60)
    print("sudo -u postgres psql -c \"CREATE USER pedro WITH PASSWORD 'cashtrack2026';\"")
    print("sudo -u postgres psql -c \"ALTER USER pedro CREATEDB;\"")
    print("sudo -u postgres psql -c \"DROP DATABASE IF EXISTS cashtrack;\"")
    print("sudo -u postgres psql -c \"CREATE DATABASE cashtrack OWNER pedro;\"")
    print("="*60)

    input("\n⏸️  Presiona ENTER cuando hayas ejecutado los comandos anteriores...")

    # 3. Verificar conexión
    print("\n3️⃣  Verificando conexión a PostgreSQL...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='cashtrack',
            user='pedro',
            password='cashtrack2026'
        )
        conn.close()
        print("✅ Conexión a PostgreSQL exitosa")
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        print("\nVerifica que hayas ejecutado los comandos de arriba correctamente")
        sys.exit(1)

    # 4. Ejecutar migración
    print("\n4️⃣  Migrando datos de SQLite a PostgreSQL...")
    result = subprocess.run([sys.executable, 'migrate_to_postgres.py'],
                          capture_output=False)

    if result.returncode != 0:
        print("❌ Error en la migración")
        sys.exit(1)

    # 5. Actualizar .env
    print("\n5️⃣  Actualizando configuración .env...")
    env_file = Path('.env')
    if env_file.exists():
        content = env_file.read_text()
        content = content.replace('DB_TYPE=sqlite', 'DB_TYPE=postgresql')
        env_file.write_text(content)
        print("✅ Archivo .env actualizado")
    else:
        print("⚠️  Archivo .env no encontrado")

    # 6. Crear backup
    print("\n6️⃣  Creando backup de SQLite...")
    from datetime import datetime
    backup_name = f"cashtrack_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    if Path('cashtrack.db').exists():
        import shutil
        shutil.copy('cashtrack.db', backup_name)
        print(f"✅ Backup creado: {backup_name}")

    # Resumen final
    print("\n" + "="*60)
    print("🎉 ¡MIGRACIÓN COMPLETADA!")
    print("="*60)
    print("\n📋 Próximos pasos:")
    print("1. Reinicia el servidor Flask")
    print("2. Verifica que todo funcione correctamente")
    print("3. El backup de SQLite está en:", backup_name)
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso cancelado por el usuario")
        sys.exit(1)
