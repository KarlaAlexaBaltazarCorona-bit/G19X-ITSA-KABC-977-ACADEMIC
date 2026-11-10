"""Herramienta de migración segura y respaldo de base de datos para LegalTech.

Garantiza:
1. Extracción en modo SOLO LECTURA sin alterar la base de datos de origen.
2. Respaldo estructurado de esquemas y registros en formato JSON reproducible.
3. Validación de conteo e integridad de registros (row count match) antes de conmutar.
"""

import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

TABLAS_ORDENADAS = [
    "users",
    "tenants",
    "organizaciones",
    "solicitud_r",
    "documento",
    "vercion_documento",
    "revicion",
    "comentarios",
    "firmas",
    "workflow_tasks",
    "chat_mensajes",
    "notificaciones",
    "auditoria",
]


def export_database(source_url: str) -> Path:
    """Extrae todas las tablas y datos de la base de datos origen sin realizar ninguna operación destructiva."""
    print("=" * 60)
    print("Iniciando respaldo de base de datos (Modo Solo Lectura)...")
    print("=" * 60)

    engine = create_engine(source_url)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"legaltech_backup_{timestamp}.json"

    data_dump = {
        "timestamp": timestamp,
        "source_server": source_url.split("@")[-1].split(":")[0] if "@" in source_url else "localhost",
        "tables": {},
    }

    with engine.connect() as conn:
        for table in TABLAS_ORDENADAS:
            if table in existing_tables:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                rows = [dict(row._mapping) for row in result]
                # Serializar fechas y UUIDs a strings
                for row in rows:
                    for k, v in row.items():
                        if v is not None and not isinstance(v, (int, float, bool, str)):
                            row[k] = str(v)
                data_dump["tables"][table] = rows
                print(f"  ✓ Tabla '{table}': {len(rows)} registros respaldados.")
            else:
                print(f"  - Tabla '{table}' no encontrada en el origen (omitida).")

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data_dump, f, indent=2, ensure_ascii=False)

    print(f"\nRespaldo completado exitosamente en: {backup_file}")
    return backup_file


def verify_integrity(source_url: str, target_url: str) -> bool:
    """Compara tabla por tabla que el conteo de registros sea idéntico entre ambos servidores."""
    print("\nValidando integridad de datos entre origen y destino...")
    src_engine = create_engine(source_url)
    tgt_engine = create_engine(target_url)

    discrepancias = 0
    with src_engine.connect() as src_conn, tgt_engine.connect() as tgt_conn:
        for table in TABLAS_ORDENADAS:
            try:
                src_count = src_conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                tgt_count = tgt_conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                if src_count == tgt_count:
                    print(f"  ✓ {table}: Coincide ({src_count} registros)")
                else:
                    print(f"  ✗ {table}: DISCREPANCIA (Origen: {src_count}, Destino: {tgt_count})")
                    discrepancias += 1
            except Exception as e:
                print(f"  ! Error al verificar tabla {table}: {e}")
                discrepancias += 1

    return discrepancias == 0


if __name__ == "__main__":
    url = os.getenv("POSTGRES_URL")
    if not url:
        print("Error: POSTGRES_URL no definida en el archivo .env")
        sys.exit(1)

    export_database(url)
