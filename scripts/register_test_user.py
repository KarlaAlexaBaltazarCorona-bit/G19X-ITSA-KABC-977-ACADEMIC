"""Script de utilidad para registrar o pre-aprobar usuarios administradores en la API de LegalTech."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("APP_API_KEY")
app_url = os.getenv("APP_SERVICE_URL", "https://app-legaltech-z5m4thvbo3byk.azurewebsites.net").rstrip("/")

if not api_key:
    print("Advertencia: APP_API_KEY no encontrada en variables de entorno.")
    api_key = input("Ingrese la API Key (X-API-KEY): ").strip()

endpoint = f"{app_url}/api/v1/users/"
headers = {
    "X-API-KEY": api_key,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

usuarios_a_registrar = [
    {
        "nombre": "Alejandro",
        "apellido": "Pruebas",
        "correo": "pruebasale25@gmail.com",
        "role": "ADMINISTRADOR_PLATAFORMA",
        "objeto_id": "9c1c0e71-37f7-4842-b534-b896b1ff6c10",
    },
    {
        "nombre": "Alejandro",
        "apellido": "Testing",
        "correo": "peuebasale25@gmail.com",
        "role": "ADMINISTRADOR_PLATAFORMA",
        "objeto_id": "c88257f7-e3d6-45dd-b171-06148b9cb1f3",
    },
]

for user_payload in usuarios_a_registrar:
    c = user_payload["correo"]
    r_role = user_payload["role"]
    print(f"Registrando usuario {c} con rol {r_role}...")
    try:
        res = requests.post(endpoint, headers=headers, json=user_payload, timeout=20)
        print(f"Resultado ({c}): Status {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Error al conectar con {endpoint}: {e}")

if __name__ == "__main__":
    pass
