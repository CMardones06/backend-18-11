
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


def test_student_not_found(auth_client, pet_payload):
    """Verifica que no se puedan consultar mascotas de un estudiante inexistente."""
    student_id = str(uuid4())

    response = auth_client.get(f"/api/students/{student_id}/pets")

    assert response.status_code == 404
    assert response.json()["message"] == "Estudiante no encontrado"


@pytest.mark.parametrize(
    "method",
    ["PATCH", "DELETE"],
    ids=["actualizar", "eliminar"],
)
def test_pet_not_found(auth_client, created_student, method):
    """Verifica que PATCH y DELETE respondan 404 si la mascota no existe."""
    student_id = created_student["id"]
    pet_id = str(uuid4())

    if method == "PATCH":
        response = auth_client.patch(
            f"/api/students/{student_id}/pets/{pet_id}",
            json={"name": "Max"},
        )
    else:
        response = auth_client.delete(
            f"/api/students/{student_id}/pets/{pet_id}"
        )

    assert response.status_code == 404
    assert response.json()["message"] == "Mascota no encontrada"


@pytest.mark.parametrize(
    "method",
    ["PATCH", "DELETE"],
    ids=["actualizar", "eliminar"],
)
def test_invalid_pet_uuid(auth_client, created_student, method):
    """Verifica que un UUID inválido para una mascota responda 404."""
    student_id = created_student["id"]
    pet_id = "no-es-un-uuid"

    if method == "PATCH":
        response = auth_client.patch(
            f"/api/students/{student_id}/pets/{pet_id}",
            json={"name": "Max"},
        )
    else:
        response = auth_client.delete(
            f"/api/students/{student_id}/pets/{pet_id}"
        )

    assert response.status_code == 404
    assert response.json()["message"] == "Mascota no encontrada"


def test_create_pet_duplicate_name(auth_client, created_student, pet_payload):
    """Verifica que un estudiante no pueda registrar dos mascotas con el mismo nombre."""
    student_id = created_student["id"]

    first_response = auth_client.post(
        f"/api/students/{student_id}/pets",
        json=pet_payload(),
    )
    assert first_response.status_code == 201

    second_response = auth_client.post(
        f"/api/students/{student_id}/pets",
        json=pet_payload(),
    )

    assert second_response.status_code == 409


def test_same_pet_name_allowed_for_different_students(
    auth_client, created_student, student_payload, pet_payload
):
    """Verifica que dos estudiantes puedan tener mascotas con el mismo nombre."""
    first_student_id = created_student["id"]

    second_student_response = auth_client.post(
        "/api/students",
        json=student_payload(
            name="Pedro Soto",
            username="pedro_soto",
            email="pedro@example.com",
        ),
    )
    assert second_student_response.status_code == 201
    second_student_id = second_student_response.json()["data"]["id"]

    first_pet_response = auth_client.post(
        f"/api/students/{first_student_id}/pets",
        json=pet_payload(),
    )
    second_pet_response = auth_client.post(
        f"/api/students/{second_student_id}/pets",
        json=pet_payload(),
    )

    assert first_pet_response.status_code == 201
    assert second_pet_response.status_code == 201
    assert (
        first_pet_response.json()["data"]["name"]
        == second_pet_response.json()["data"]["name"]
    )


@pytest.mark.parametrize(
    "method",
    ["PATCH", "DELETE"],
    ids=["actualizar", "eliminar"],
)
def test_cannot_modify_another_students_pet(
    auth_client, created_student, student_payload, created_pet, method
):
    """Verifica que un estudiante no pueda modificar ni eliminar la mascota de otro."""
    second_student_response = auth_client.post(
        "/api/students",
        json=student_payload(
            name="Pedro Soto",
            username="pedro_soto",
            email="pedro@example.com",
        ),
    )
    assert second_student_response.status_code == 201
    second_student_id = second_student_response.json()["data"]["id"]

    pet_id = created_pet["id"]

    if method == "PATCH":
        response = auth_client.patch(
            f"/api/students/{second_student_id}/pets/{pet_id}",
            json={"name": "Max"},
        )
    else:
        response = auth_client.delete(
            f"/api/students/{second_student_id}/pets/{pet_id}"
        )

    assert response.status_code == 404
    assert response.json()["message"] == "Mascota no encontrada"

def test_update_pet_duplicate_name_returns_409(
    auth_client, created_student, created_pet, pet_payload
):
    """Verifica que PATCH devuelva 409 si se usa el nombre de otra mascota del estudiante."""
    student_id = created_student["id"]

    second_pet_resp = auth_client.post(
        f"/api/students/{student_id}/pets",
        json=pet_payload(name="Michi", species="gato"),
    )
    assert second_pet_resp.status_code == 201
    second_pet_id = second_pet_resp.json()["data"]["id"]

    response = auth_client.patch(
        f"/api/students/{student_id}/pets/{second_pet_id}",
        json={"name": created_pet["name"]},
    )

    assert response.status_code == 409


def test_update_pet_keeping_same_name_returns_200(
    auth_client, created_student, created_pet
):
    """Verifica que PATCH permita conservar el mismo nombre actual de la mascota."""
    student_id = created_student["id"]
    pet_id = created_pet["id"]

    response = auth_client.patch(
        f"/api/students/{student_id}/pets/{pet_id}",
        json={"name": created_pet["name"], "age": 4},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == created_pet["name"]
    assert data["age"] == 4


def test_update_pet_rejects_extra_fields(auth_client, created_student, created_pet):
    """Verifica que PATCH rechace campos no declarados en UpdatePetDto con 400."""
    student_id = created_student["id"]
    pet_id = created_pet["id"]

    response = auth_client.patch(
        f"/api/students/{student_id}/pets/{pet_id}",
        json={"color": "negro"},
    )

    assert response.status_code == 400
    assert response.json()["errors"] == {}


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("POST", "", {"name": "Firulais", "species": "perro", "age": 3}),
        ("PATCH", f"/{uuid4()}", {"name": "Max"}),
        ("DELETE", f"/{uuid4()}", None),
    ],
    ids=["crear", "actualizar", "eliminar"],
)
def test_mutations_with_nonexistent_student_return_404(
    auth_client, method, suffix, payload
):
    """Verifica que POST, PATCH y DELETE respondan 404 si el estudiante no existe."""
    url = f"/api/students/{uuid4()}/pets{suffix}"
    response = auth_client.request(method, url, json=payload)

    assert response.status_code == 404
    assert response.json()["message"] == "Estudiante no encontrado"


def test_invalid_student_uuid_returns_404(auth_client):
    """Verifica que un UUID de estudiante inválido responda 404."""
    response = auth_client.get("/api/students/no-es-un-uuid/pets")

    assert response.status_code == 404
    assert response.json()["message"] == "Estudiante no encontrado"


def test_delete_pet_twice_returns_404(auth_client, created_student, created_pet):
    """Verifica que intentar eliminar una mascota ya eliminada responda 404."""
    student_id = created_student["id"]
    pet_id = created_pet["id"]

    first_delete = auth_client.delete(f"/api/students/{student_id}/pets/{pet_id}")
    assert first_delete.status_code == 200

    second_delete = auth_client.delete(f"/api/students/{student_id}/pets/{pet_id}")
    assert second_delete.status_code == 404
    assert second_delete.json()["message"] == "Mascota no encontrada"