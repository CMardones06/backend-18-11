"""Pruebas unitarias de los schemas de Pet.

Validan las reglas de entrada sin base de datos ni HTTP. Son la primera
barrera para que un payload inválido no llegue al servicio.
"""

import pytest
from pydantic import ValidationError

from app.pets.schemas import CreatePetDto, UpdatePetDto

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# CreatePetDto
# ---------------------------------------------------------------------------


def test_create_pet_valid(pet_payload):
    """
    Verifica que un payload válido construya el DTO con los datos esperados.
    """
    dto = CreatePetDto(**pet_payload())

    assert dto.name == "Firulais"
    assert dto.species == "perro"
    assert dto.age == 3


def test_create_pet_without_age(pet_payload):
    """
    Verifica que `age` sea opcional al crear una mascota y quede en `None`.
    """
    payload = pet_payload()
    payload.pop("age", None)

    dto = CreatePetDto(**payload)

    assert dto.name == "Firulais"
    assert dto.species == "perro"
    assert dto.age is None


@pytest.mark.parametrize("age", [0, 100], ids=["minimo-0", "maximo-100"])
def test_create_pet_valid_boundary_ages(pet_payload, age):
    """Verifica que los valores límite de edad (0 y 100) sean aceptados."""
    dto = CreatePetDto(**pet_payload(age=age))

    assert dto.age == age


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "El nombre no puede estar vacío"),
        ("a" * 51, "El nombre debe tener entre 1 y 50 caracteres"),
        ("<b>Firulais</b>", "No se permiten etiquetas HTML"),
        (123, "El nombre debe ser un texto"),
        (None, "El nombre debe ser un texto"),
    ],
    ids=["vacio", "largo", "html", "no-texto", "none"],
)
def test_create_pet_invalid_name(pet_payload, name, message):
    """
    Verifica que los nombres inválidos se rechacen con el mensaje de su regla.

    Cubre vacío, longitud máxima, etiquetas HTML y tipo incorrecto.
    """
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(name=name))

    assert message in str(error.value)


@pytest.mark.parametrize(
    ("species", "message"),
    [
        ("", "La especie no puede estar vacía"),
        ("a" * 51, "La especie debe tener entre 1 y 50 caracteres"),
        ("<script>gato</script>", "No se permiten etiquetas HTML"),
        (123, "La especie debe ser un texto"),
        (None, "La especie debe ser un texto"),
    ],
    ids=["vacio", "largo", "html", "no-texto", "none"],
)
def test_create_pet_invalid_species(pet_payload, species, message):
    """
    Verifica que las especies inválidas se rechacen con su mensaje.

    Cubre vacío, longitud máxima, etiquetas HTML y tipo incorrecto.
    """
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(species=species))

    assert message in str(error.value)


@pytest.mark.parametrize(
    ("age", "message"),
    [
        (-1, "La edad debe ser al menos 0"),
        (101, "La edad debe ser como máximo 100"),
        (2.5, "La edad debe ser un número entero"),
        (True, "La edad debe ser un número entero"),
        ("3", "La edad debe ser un número entero"),
    ],
    ids=["menor", "mayor", "decimal", "booleano", "texto"],
)
def test_create_pet_invalid_age(pet_payload, age, message):
    """Verifica que las edades fuera de rango o de tipo incorrecto se rechacen."""
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(age=age))

    assert message in str(error.value)


def test_create_pet_rejects_extra_fields(pet_payload):
    """Verifica que un campo no declarado se rechace con `extra_forbidden`."""
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(extra="no permitido"))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


# ---------------------------------------------------------------------------
# UpdatePetDto
# ---------------------------------------------------------------------------


def test_update_pet_all_fields_optional():
    """
    Verifica que todos los campos de actualización sean opcionales.

    Espera un DTO con todos los valores en `None`.
    """
    dto = UpdatePetDto()

    assert dto.model_dump() == {
        "name": None,
        "species": None,
        "age": None,
    }


def test_update_pet_partial():
    """Verifica que una actualización parcial deje el resto de campos en `None`."""
    dto = UpdatePetDto(name="Michi", age=4)

    assert dto.name == "Michi"
    assert dto.age == 4
    assert dto.species is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "a" * 51, "El nombre debe tener entre 1 y 50 caracteres"),
        ("name", "<b>Michi</b>", "No se permiten etiquetas HTML"),
        ("name", 123, "El nombre debe ser un texto"),
        ("species", "a" * 51, "La especie debe tener entre 1 y 50 caracteres"),
        ("species", "<gato>", "No se permiten etiquetas HTML"),
        ("species", 123, "La especie debe ser un texto"),
        ("age", -1, "La edad debe ser al menos 0"),
        ("age", 101, "La edad debe ser como máximo 100"),
        ("age", "3", "La edad debe ser un número entero"),
    ],
    ids=[
        "nombre-largo",
        "nombre-html",
        "nombre-tipo",
        "especie-larga",
        "especie-html",
        "especie-tipo",
        "edad-menor",
        "edad-mayor",
        "edad-tipo",
    ],
)
def test_update_pet_invalid_values(field, value, message):
    """Verifica que los valores inválidos se rechacen al actualizar."""
    with pytest.raises(ValidationError) as error:
        UpdatePetDto(**{field: value})

    assert message in str(error.value)


@pytest.mark.parametrize(
    "field",
    ["name", "species", "age"],
    ids=["nombre", "especie", "edad"],
)
def test_update_pet_accepts_none(field):
    """Verifica que `None` sea aceptado en cada campo opcional."""
    dto = UpdatePetDto(**{field: None})

    assert getattr(dto, field) is None


def test_update_pet_rejects_extra_fields():
    """Verifica que un campo no declarado se rechace al actualizar."""
    with pytest.raises(ValidationError) as error:
        UpdatePetDto(extra="no permitido")

    assert error.value.errors()[0]["type"] == "extra_forbidden"