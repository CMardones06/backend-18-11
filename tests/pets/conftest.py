"""Fixtures compartidos para los tests del módulo Pets."""

import pytest


@pytest.fixture
def student_payload():
    """Devuelve una fábrica de payloads válidos para crear estudiantes."""

    def build(**overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "name": "Ana Pérez",
            "username": "ana_perez",
            "email": "ana@example.com",
            "age": 21,
        }
        data.update(overrides)
        return data

    return build


@pytest.fixture
def pet_payload():
    """Devuelve una fábrica de payloads válidos para crear mascotas."""

    def build(**overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "name": "Firulais",
            "species": "perro",
            "age": 3,
        }
        data.update(overrides)
        return data

    return build


@pytest.fixture
def created_student(auth_client, student_payload) -> dict[str, object]:
    """Crea un estudiante autenticado y devuelve los datos de la respuesta."""
    response = auth_client.post("/api/students", json=student_payload())
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.fixture
def created_pet(auth_client, created_student, pet_payload) -> dict[str, object]:
    """Crea una mascota asociada al estudiante y devuelve sus datos."""
    student_id = created_student["id"]
    response = auth_client.post(
        f"/api/students/{student_id}/pets", json=pet_payload()
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]