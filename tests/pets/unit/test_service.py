
"""Pruebas unitarias de PetsService.

Usan repositorios falsos para aislar la lógica de negocio.
No utilizan PostgreSQL ni realizan solicitudes HTTP.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.pets.models import PetModel
from app.pets.schemas import CreatePetDto, UpdatePetDto
from app.pets.service import PetsService
from app.shared.datetimes import utc_now

pytestmark = pytest.mark.unit


class FakePetsRepository:
    """Repositorio en memoria para probar PetsService."""

    def __init__(self):
        self.pets = []

    def find_all_by_student(self, student_id):
        return [
            pet for pet in self.pets
            if pet.studentId == student_id
        ]

    def find_by_id(self, pet_id):
        return next(
            (pet for pet in self.pets if pet.id == pet_id),
            None,
        )

    def find_by_student_and_name(self, student_id, name):
        return next(
            (
                pet for pet in self.pets
                if pet.studentId == student_id and pet.name == name
            ),
            None,
        )

    def add(self, pet):
        pet.id = uuid4()
        now = utc_now()
        pet.createdAt = now
        pet.updatedAt = now
        self.pets.append(pet)
        return pet

    def delete(self, pet):
        self.pets.remove(pet)


@pytest.fixture
def student():
    """Crea un estudiante simulado con identificador."""

    return SimpleNamespace(id=uuid4())


@pytest.fixture
def fake_pets_repository():
    """Entrega un repositorio de mascotas en memoria."""

    return FakePetsRepository()


@pytest.fixture
def service(fake_pets_repository, student):
    """Crea PetsService con dependencias simuladas."""

    db = MagicMock()
    pets_service = PetsService(db)

    pets_service.repository = fake_pets_repository
    pets_service.students_service = MagicMock()
    pets_service.students_service.get_or_404.return_value = student

    return pets_service


@pytest.fixture
def pet_payload():
    """Devuelve una fábrica de datos válidos para crear mascotas."""

    def build(**overrides):
        data = {
            "name": "Firulais",
            "species": "perro",
            "age": 3,
        }
        data.update(overrides)
        return data

    return build


@pytest.fixture
def make_pet_model(student):
    """Devuelve una fábrica de PetModel con id y fechas asignados."""

    def build(**overrides):
        now = utc_now()
        values = {
            "id": uuid4(),
            "studentId": student.id,
            "name": "Firulais",
            "species": "perro",
            "age": 3,
            "createdAt": now,
            "updatedAt": now,
        }
        values.update(overrides)
        return PetModel(**values)

    return build


def test_find_all_for_student(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
):
    """Verifica que el listado devuelva las mascotas del estudiante."""

    fake_pets_repository.pets.extend(
        [
            make_pet_model(name="Firulais"),
            make_pet_model(name="Michi", species="gato"),
        ]
    )

    result = service.find_all_for_student(str(student.id))

    assert result.total == 2
    assert [pet.name for pet in result.items] == ["Firulais", "Michi"]


def test_find_all_for_student_empty(
    service,
    student,
):
    """Verifica que un estudiante sin mascotas obtenga una lista vacía."""

    result = service.find_all_for_student(str(student.id))

    assert result.total == 0
    assert result.items == []


def test_find_all_for_student_missing_student(service):
    """Verifica que un estudiante inexistente produzca un error 404."""

    service.students_service.get_or_404.side_effect = HTTPException(
        status_code=404,
        detail="Estudiante no encontrado",
    )

    with pytest.raises(HTTPException) as error:
        service.find_all_for_student(str(uuid4()))

    assert error.value.status_code == 404


def test_create(
    service,
    fake_pets_repository,
    student,
    pet_payload,
):
    """Verifica que crear una mascota la agregue y haga commit."""

    result = service.create(
        str(student.id),
        CreatePetDto(**pet_payload()),
    )

    assert result.name == "Firulais"
    assert result.species == "perro"
    assert result.age == 3
    assert result.studentId == student.id
    assert len(fake_pets_repository.pets) == 1
    service.db.commit.assert_called_once()


def test_create_duplicate_name(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
    pet_payload,
):
    """Verifica que no se puedan repetir nombres para un estudiante."""

    fake_pets_repository.pets.append(make_pet_model())

    with pytest.raises(HTTPException) as error:
        service.create(
            str(student.id),
            CreatePetDto(**pet_payload()),
        )

    assert error.value.status_code == 409
    service.db.commit.assert_not_called()


def test_create_same_name_for_another_student(
    service,
    fake_pets_repository,
    student,
    pet_payload,
):
    """Verifica que otro estudiante pueda usar el mismo nombre."""

    other_student_id = uuid4()

    fake_pets_repository.pets.append(
        PetModel(
            id=uuid4(),
            studentId=other_student_id,
            name="Firulais",
            species="perro",
            age=3,
            createdAt=utc_now(),
            updatedAt=utc_now(),
        )
    )

    result = service.create(
        str(student.id),
        CreatePetDto(**pet_payload()),
    )

    assert result.name == "Firulais"
    service.db.commit.assert_called_once()


def test_update_partial(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
):
    """Verifica que actualizar una mascota modifique solo lo enviado."""

    pet = make_pet_model()
    fake_pets_repository.pets.append(pet)

    result = service.update(
        str(student.id),
        str(pet.id),
        UpdatePetDto(name="Firulais Nuevo", age=5),
    )

    assert result.name == "Firulais Nuevo"
    assert result.age == 5
    assert result.species == "perro"
    service.db.commit.assert_called_once()


def test_update_empty(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
):
    """Verifica que una actualización vacía conserve los datos."""

    pet = make_pet_model()
    fake_pets_repository.pets.append(pet)

    result = service.update(
        str(student.id),
        str(pet.id),
        UpdatePetDto(),
    )

    assert result.name == "Firulais"
    assert result.species == "perro"
    assert result.age == 3
    service.db.commit.assert_called_once()


def test_update_duplicate_name(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
):
    """Verifica que cambiar al nombre de otra mascota produzca 409."""

    first = make_pet_model(name="Firulais")
    second = make_pet_model(name="Michi")
    fake_pets_repository.pets.extend([first, second])

    with pytest.raises(HTTPException) as error:
        service.update(
            str(student.id),
            str(first.id),
            UpdatePetDto(name="Michi"),
        )

    assert error.value.status_code == 409
    service.db.commit.assert_not_called()


def test_update_allows_same_name(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
):
    """Verifica que la mascota pueda conservar su propio nombre."""

    pet = make_pet_model()
    fake_pets_repository.pets.append(pet)

    result = service.update(
        str(student.id),
        str(pet.id),
        UpdatePetDto(name="Firulais"),
    )

    assert result.name == "Firulais"
    service.db.commit.assert_called_once()


def test_update_missing_pet_returns_404(
    service,
    student,
):
    """Verifica que actualizar una mascota inexistente produzca 404."""

    with pytest.raises(HTTPException) as error:
        service.update(
            str(student.id),
            str(uuid4()),
            UpdatePetDto(name="Nuevo nombre"),
        )

    assert error.value.status_code == 404
    service.db.commit.assert_not_called()


def test_update_invalid_pet_id_returns_404(
    service,
    student,
):
    """Verifica que un identificador inválido produzca 404."""

    with pytest.raises(HTTPException) as error:
        service.update(
            str(student.id),
            "no-es-un-uuid",
            UpdatePetDto(name="Nuevo nombre"),
        )

    assert error.value.status_code == 404


def test_delete(
    service,
    fake_pets_repository,
    student,
    make_pet_model,
):
    """Verifica que eliminar una mascota la quite y haga commit."""

    pet = make_pet_model()
    fake_pets_repository.pets.append(pet)

    result = service.delete(str(student.id), str(pet.id))

    assert result.id == pet.id
    assert result.name == "Firulais"
    assert fake_pets_repository.pets == []
    service.db.commit.assert_called_once()


def test_delete_missing_pet_returns_404(
    service,
    student,
):
    """Verifica que eliminar una mascota inexistente produzca 404."""

    with pytest.raises(HTTPException) as error:
        service.delete(str(student.id), str(uuid4()))

    assert error.value.status_code == 404
    service.db.commit.assert_not_called()


def test_find_owned_rejects_pet_from_another_student(
    service,
    fake_pets_repository,
    make_pet_model,
):
    """Verifica que un estudiante no pueda acceder a mascotas ajenas."""

    pet = make_pet_model(studentId=uuid4())
    fake_pets_repository.pets.append(pet)

    with pytest.raises(HTTPException) as error:
        service.find_owned(str(uuid4()), str(pet.id))

    assert error.value.status_code == 404


def test_find_owned_rejects_missing_student(service):
    """Verifica que buscar una mascota de un estudiante inexistente falle."""

    service.students_service.get_or_404.side_effect = HTTPException(
        status_code=404,
        detail="Estudiante no encontrado",
    )

    with pytest.raises(HTTPException) as error:
        service.find_owned(str(uuid4()), str(uuid4()))

    assert error.value.status_code == 404
