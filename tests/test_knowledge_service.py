"""
Pruebas del knowledge de auditoría local.

El servicio lee `backend/data/knowledge_ips.json`. Aquí se dobla `_load_entries`
(único punto que toca el disco) para probar el matching y el renderizado sin
depender del contenido real del archivo.
"""

from pathlib import Path

import pytest

from backend.schemas.knowledge_schemas import (
    KnowledgeCategory,
    KnowledgeContext,
    KnowledgeEntry,
)
from backend.services.knowledge_service import (
    MAX_ENTRIES_IN_PROMPT,
    KnowledgeAuditService,
)


def entrada(
    trigger_key: str,
    *,
    categoria=KnowledgeCategory.GENERAL,
    ambito="GLOBAL",
    directriz="Verificar contra los KPIs.",
    evidencia=None,
    prioridad=3,
    id_=1,
) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=id_,
        trigger_key=trigger_key,
        categoria=categoria,
        ambito=ambito,
        directriz=directriz,
        criterios_evidencia=evidencia,
        prioridad=prioridad,
    )


@pytest.fixture
def service(monkeypatch):
    """Servicio con la lectura del archivo sustituida por una lista fija."""
    svc = KnowledgeAuditService()

    def _set_entries(entries):
        monkeypatch.setattr(svc, "_load_entries", lambda: list(entries))
        return svc

    return _set_entries


# ============================================================
# MATCHING
# ============================================================

async def test_match_ignora_acentos_y_mayusculas(service):
    svc = service([entrada("camas", categoria=KnowledgeCategory.CAPACIDAD)])

    ctx = await svc.build_context("Analiza la capacidad en CAMAS de Antioquia")

    assert len(ctx.entradas) == 1


async def test_match_requiere_palabra_completa(service):
    """
    'cama' no debe coincidir dentro de 'camaleon'. El matching por subcadena
    produce falsos positivos.
    """
    svc = service([entrada("cama", categoria=KnowledgeCategory.CAPACIDAD)])

    ctx = await svc.build_context("Analiza el camaleon de la region")

    assert ctx.entradas == []


async def test_match_respeta_acentos_en_el_trigger(service):
    """El trigger_key con acento debe casar con la consulta acentuada y sin acentuar."""
    svc = service([entrada("atención primaria")])

    assert len((await svc.build_context("necesito atencion primaria")).entradas) == 1
    assert len((await svc.build_context("necesito atención primaria")).entradas) == 1


async def test_sin_coincidencias_devuelve_contexto_vacio(service):
    svc = service([entrada("ambulancias")])

    ctx = await svc.build_context("cuantas IPS hay en Antioquia")

    assert ctx.entradas == []
    assert ctx.como_prompt() == "", "un contexto vacío no debe generar encabezado"


# ============================================================
# FILTROS
# ============================================================

async def test_filtro_por_categoria(service):
    svc = service([
        entrada("camas", id_=1, categoria=KnowledgeCategory.CAPACIDAD),
        entrada("camas por nivel", id_=2, categoria=KnowledgeCategory.COBERTURA),
    ])

    ctx = await svc.build_context("analiza las camas", categorias=["capacidad"])

    assert [e.id for e in ctx.entradas] == [1]


async def test_entrada_de_ambito_solo_aplica_a_su_territorio(service):
    svc = service([
        entrada("camas", id_=1, ambito="antioquia", prioridad=3),
        entrada("camas", id_=2, ambito="GLOBAL", prioridad=2),
    ])

    ctx_antioquia = await svc.build_context("camas en antioquia")
    ctx_caldas = await svc.build_context("camas en caldas")

    # Ordenado por (prioridad, id): la GLOBAL tiene prioridad 2, así que va primera.
    assert [e.id for e in ctx_antioquia.entradas] == [2, 1]
    assert [e.id for e in ctx_caldas.entradas] == [2], "GLOBAL siempre aplica; el resto no"


# ============================================================
# RECORTE POR PRIORIDAD
# ============================================================

async def test_recorta_por_prioridad_no_por_orden_de_insercion(service):
    svc = service([
        entrada("camas", id_=1, prioridad=5),
        entrada("camas", id_=2, prioridad=1),
        entrada("camas", id_=3, prioridad=3),
    ])

    ctx = await svc.build_context("camas", max_entries=2)

    assert [e.id for e in ctx.entradas] == [2, 3]


async def test_limite_por_defecto(service):
    entradas = [entrada("camas", id_=i, prioridad=(i % 5) + 1) for i in range(1, 8)]
    svc = service(entradas)

    ctx = await svc.build_context("camas")

    assert len(ctx.entradas) == MAX_ENTRIES_IN_PROMPT


# ============================================================
# DEGRADACION
# ============================================================

async def test_consulta_vacia_no_lee_el_archivo(monkeypatch):
    llamadas = []

    svc = KnowledgeAuditService()

    def _load():
        llamadas.append(1)
        return []

    monkeypatch.setattr(svc, "_load_entries", _load)

    ctx = await svc.build_context("   ")

    assert ctx.entradas == []
    assert llamadas == []


async def test_archivo_inexistente_degrada_a_contexto_vacio():
    """El knowledge es opcional: si falta el archivo, el pipeline sigue."""
    svc = KnowledgeAuditService(path=Path("no_existe_knowledge.json"))

    assert svc.available is False
    ctx = await svc.build_context("analiza las camas")

    assert ctx.entradas == []
    assert ctx.como_prompt() == ""


# ============================================================
# ARCHIVO REAL DEL ASISTENTE
# ============================================================

async def test_el_archivo_real_carga_y_matchea():
    """El knowledge entregado con el repo debe parsear y responder a 'camas'."""
    svc = KnowledgeAuditService()

    assert svc.available is True, "falta backend/data/knowledge_ips.json"
    ctx = await svc.build_context("cuantas camas hay en Antioquia")

    assert ctx.entradas, "el archivo real deberia tener una directriz sobre camas"
    assert any("camas" in e.trigger_key for e in ctx.entradas)


# ============================================================
# RENDERIZADO DEL PROMPT
# ============================================================

def test_como_prompt_incluye_directriz_y_evidencia():
    ctx = KnowledgeContext(
        entradas=[entrada(
            "camas",
            categoria=KnowledgeCategory.CAPACIDAD,
            directriz="Revisar la dotacion de camas.",
            evidencia="Suma de capacidad por grupo.",
            prioridad=1,
        )],
        consulta="analiza las camas",
    )

    bloque = ctx.como_prompt()

    assert "Revisar la dotacion de camas." in bloque
    assert "Evidencia requerida: Suma de capacidad por grupo." in bloque
    assert "capacidad" in bloque


def test_como_prompt_ordena_por_prioridad():
    ctx = KnowledgeContext(entradas=[
        entrada("a", id_=1, prioridad=5, directriz="Quinta."),
        entrada("b", id_=2, prioridad=1, directriz="Primera."),
    ])

    bloque = ctx.como_prompt()

    assert bloque.index("Primera.") < bloque.index("Quinta.")


def test_como_prompt_sin_entradas_no_cuesta_tokens():
    """Un encabezado sin contenido es costo sin información (AGENTS.md 4.6)."""
    assert KnowledgeContext(entradas=[], consulta="x").como_prompt() == ""


# ============================================================
# CONTRATO DEL SCHEMA
# ============================================================

def test_entrada_rechaza_prioridad_fuera_de_rango():
    with pytest.raises(ValueError):
        entrada("camas", prioridad=9)


def test_categoria_desconocida_falla_validacion():
    with pytest.raises(ValueError):
        KnowledgeEntry(
            id=1,
            trigger_key="camas",
            categoria="categoria_inexistente",
            directriz="x",
        )
