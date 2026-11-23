
"""Pruebas E2E de la API de Pets (enfocadas en contratos y schemas)."""

from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("GET", "", None),
        ("POST", "", {"name": "Firulais", "species": "perro", "age": 3}),
        ("PATCH", f"/{uuid4()}", {"name": "Michi"}),
        ("DELETE", f"/{uuid4()}", None),
    ],
    ids=["listar", "crear", "actualizar", "eliminar"],
)
def test_requires_session(client, method, suffix, payload):
    """Verifica que los endpoints de Pets rechacen peticiones sin sesión con 401."""
    url = f"/api/students/{uuid4()}/pets{suffix}"
    response = client.request(method, url, json=payload)

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]


def test_create_pet_valid_schema(auth_client, created_student, pet_payload):
    """Verifica que POST con datos válidos responda 201 y cumpla el schema Pet."""
    student_id = created_student["id"]
    response = auth_client.post(
        f"/api/students/{student_id}/pets", json=pet_payload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 201
    assert body["success"] is True
    assert body["message"] == "Recurso creado"

    data = body["data"]
    assert UUID(data["id"])
    assert data["studentId"] == student_id
    assert data["name"] == "Firulais"
    assert data["species"] == "perro"
    assert data["age"] == 3
    assert data["createdAt"].endswith("Z")
    assert data["updatedAt"].endswith("Z")


def test_create_pet_without_optional_age(auth_client, created_student, pet_payload):
    """Verifica que crear una mascota omitiendo age responda con age None."""
    student_id = created_student["id"]
    payload = pet_payload()
    payload.pop("age")

    response = auth_client.post(f"/api/students/{student_id}/pets", json=payload)

    assert response.status_code == 201
    assert response.json()["data"]["age"] is None


def test_list_empty(auth_client, created_student):
    """Verifica el listado cuando el estudiante no tiene mascotas."""
    student_id = created_student["id"]
    response = auth_client.get(f"/api/students/{student_id}/pets")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "Operación exitosa"
    assert body["data"] == {"total": 0, "items": []}


def test_list_pets_schema(auth_client, created_student, created_pet):
    """Verifica que GET devuelva el envelope con la estructura PetList."""
    student_id = created_student["id"]
    response = auth_client.get(f"/api/students/{student_id}/pets")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == created_pet["id"]


def test_create_pet_validation_errors(auth_client, created_student, pet_payload):
    """Verifica que campos inválidos devuelvan 400 con detalle por campo."""
    student_id = created_student["id"]
    response = auth_client.post(
        f"/api/students/{student_id}/pets",
        json=pet_payload(
            name="<b>Firulais</b>",
            species="",
            age=101,
        ),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Error de validación"
    errors = body["errors"]
    assert set(errors) == {"name", "species", "age"}
    assert "No se permiten etiquetas HTML" in errors["name"]["message"]
    assert "no puede estar vacía" in errors["species"]["message"]
    assert "como máximo 100" in errors["age"]["message"]


def test_create_pet_missing_fields(auth_client, created_student):
    """Verifica que enviar un JSON vacío devuelva 400 exigiendo name y species."""
    student_id = created_student["id"]
    response = auth_client.post(f"/api/students/{student_id}/pets", json={})

    assert response.status_code == 400
    errors = response.json()["errors"]
    assert set(errors) == {"name", "species"}
    assert "El nombre debe ser un texto" in errors["name"]["message"]
    assert "La especie debe ser un texto" in errors["species"]["message"]


def test_create_pet_rejects_extra_fields(auth_client, created_student, pet_payload):
    """Verifica que un campo extra no declarado en CreatePetDto devuelva 400."""
    student_id = created_student["id"]
    response = auth_client.post(
        f"/api/students/{student_id}/pets",
        json=pet_payload(color="café"),
    )

    assert response.status_code == 400
    assert response.json()["errors"] == {}


def test_update_pet_partial_and_validation(auth_client, created_student, created_pet):
    """Verifica actualización parcial válida y rechazo de datos inválidos."""
    student_id = created_student["id"]
    pet_id = created_pet["id"]

    ok_response = auth_client.patch(
        f"/api/students/{student_id}/pets/{pet_id}",
        json={"name": "Max"},
    )

    assert ok_response.status_code == 200
    assert ok_response.json()["data"]["name"] == "Max"
    assert ok_response.json()["data"]["species"] == created_pet["species"]

    bad_response = auth_client.patch(
        f"/api/students/{student_id}/pets/{pet_id}",
        json={"age": -5},
    )
    assert bad_response.status_code == 400
    assert "age" in bad_response.json()["errors"]


def test_delete_pet(auth_client, created_student, created_pet):
    """Verifica que DELETE elimine correctamente una mascota."""
    student_id = created_student["id"]
    pet_id = created_pet["id"]

    response = auth_client.delete(
        f"/api/students/{student_id}/pets/{pet_id}"
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == pet_id

    get_response = auth_client.get(
        f"/api/students/{student_id}/pets"
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["total"] == 0
