"""Pruebas E2E de la API de Pet.

Usan TestClient, una base PostgreSQL real y una sesión autenticada.
Cubren el recorrido completo: router, dependencias, servicio, repositorio
y envelope de respuesta.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.pets.models import PetModel

pytestmark = pytest.mark.e2e


def create_pet(client, payload):
    """Crea una mascota por HTTP y devuelve el contenido de `data`."""
    response = client.post("/api/pets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/pets", None),
        ("GET", f"/api/pets/{uuid4()}", None),
        (
            "POST",
            "/api/pets",
            {
                "name": "Firulais",
                "species": "perro",
                "age": 3,
                "studentId": str(uuid4()),
            },
        ),
        ("PATCH", f"/api/pets/{uuid4()}", {"name": "Nombre Nuevo"}),
        ("DELETE", f"/api/pets/{uuid4()}", None),
    ],
    ids=["listar", "obtener", "crear", "actualizar", "eliminar"],
)
def test_requires_session(client, method, path, payload):
    """Verifica que los endpoints de Pet rechacen peticiones sin sesión."""
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]


def test_list_empty(auth_client):
    """Verifica el listado cuando no hay mascotas."""
    response = auth_client.get("/api/pets")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "Operación exitosa"
    assert body["data"] == {"total": 0, "items": []}


def test_create_pet(auth_client, pet_payload, created_student):
    """Verifica el alta de una mascota autenticada."""
    data = pet_payload(studentId=created_student["id"])
    response = auth_client.post("/api/pets", json=data)

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 201
    assert body["success"] is True
    assert body["message"] == "Recurso creado"
    res_data = body["data"]
    assert res_data["name"] == "Firulais"
    assert res_data["species"] == "perro"
    assert res_data["age"] == 3
    assert UUID(res_data["id"])


def test_get_pet_by_id(auth_client, created_pet):
    """Verifica que GET por id devuelva la mascota creada."""
    response = auth_client.get(f"/api/pets/{created_pet['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == created_pet["id"]


def test_update_pet(auth_client, created_pet):
    """Verifica que PATCH actualice solo el campo enviado."""
    response = auth_client.patch(
        f"/api/pets/{created_pet['id']}",
        json={"name": "Scooby"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Recurso actualizado"
    assert body["data"]["name"] == "Scooby"
    assert body["data"]["species"] == created_pet["species"]


def test_delete_pet(auth_client, created_pet):
    """Verifica que DELETE elimine la mascota correctamente."""
    response = auth_client.delete(f"/api/pets/{created_pet['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Recurso eliminado"
    assert body["data"]["id"] == created_pet["id"]

    get_response = auth_client.get(f"/api/pets/{created_pet['id']}")
    assert get_response.status_code == 404
