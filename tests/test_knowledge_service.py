"""
Pruebas del knowledge de auditoría parametrizable.

El servicio se prueba sin red: se dobla `_fetch_entries`, que es el único punto
que habla con Supabase. Lo que importa aquí es el matching y el renderizado del
prompt.
"""

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
    mercado="GLOBAL",
    directriz="Verificar contra los KPIs.",
    evidencia=None,
    prioridad=3,
    id_=1,
) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=id_,
        trigger_key=trigger_key,
        categoria=categoria,
        mercado=mercado,
        directriz=directriz,
        criterios_evidencia=evidencia,
        prioridad=prioridad,
    )


@pytest.fixture
def service(monkeypatch):
    """Servicio con la lectura de Supabase sustituida por una lista fija."""
    svc = KnowledgeAuditService()

    def _set_entries(entries):
        async def _fetch():
            return list(entries)

        monkeypatch.setattr(svc, "_fetch_entries", _fetch)
        return svc

    return _set_entries


# ============================================================
# MATCHING
# ============================================================

async def test_match_ignora_acentos_y_mayusculas(service):
    svc = service([entrada("movil", categoria=KnowledgeCategory.DISPOSITIVO)])

    ctx = await svc.build_context("Analiza el comportamiento en MOVIL")

    assert len(ctx.entradas) == 1


async def test_match_requiere_palabra_completa(service):
    """
    'pais' no debe coincidir dentro de 'paisaje'. El matching por subcadena ya
    produjo falsos positivos en `match_country`.
    """
    svc = service([entrada("pais", categoria=KnowledgeCategory.MERCADO)])

    ctx = await svc.build_context("Analiza el paisaje de la region")

    assert ctx.entradas == []


async def test_match_respeta_acentos_en_el_trigger(service):
    """El trigger_key con acento debe casar con la consulta acentuada y sin acentuar."""
    svc = service([entrada("atención al cliente")])

    assert len((await svc.build_context("necesito atencion al cliente")).entradas) == 1
    assert len((await svc.build_context("necesito atención al cliente")).entradas) == 1


async def test_sin_coincidencias_devuelve_contexto_vacio(service):
    svc = service([entrada("checkout")])

    ctx = await svc.build_context("cuantos usuarios hay en colombia")

    assert ctx.entradas == []
    assert ctx.como_prompt() == "", "un contexto vacío no debe generar encabezado"


# ============================================================
# FILTROS
# ============================================================

async def test_filtro_por_categoria(service):
    svc = service([
        entrada("checkout", id_=1, categoria=KnowledgeCategory.FRICCION),
        entrada("checkout lento", id_=2, categoria=KnowledgeCategory.COMPORTAMIENTO),
    ])

    ctx = await svc.build_context("analiza el checkout", categorias=["friccion"])

    assert [e.id for e in ctx.entradas] == [1]


async def test_entrada_de_mercado_solo_aplica_a_su_mercado(service):
    svc = service([
        entrada("checkout", id_=1, mercado="colombia", prioridad=3),
        entrada("checkout", id_=2, mercado="GLOBAL", prioridad=2),
    ])

    ctx_colombia = await svc.build_context("checkout en colombia")
    ctx_peru = await svc.build_context("checkout en peru")

    # Ordenado por (prioridad, id): la GLOBAL tiene prioridad 2, así que va primera.
    assert [e.id for e in ctx_colombia.entradas] == [2, 1]
    assert [e.id for e in ctx_peru.entradas] == [2], "GLOBAL siempre aplica; el resto no"


# ============================================================
# RECORTE POR PRIORIDAD
# ============================================================

async def test_recorta_por_prioridad_no_por_orden_de_insercion(service):
    """
    `prioridad.asc` viene del ORDER BY, pero el recorte debe tolerar que el
    servicio se llame con entradas desordenadas.
    """
    svc = service([
        entrada("checkout", id_=1, prioridad=5),
        entrada("checkout", id_=2, prioridad=1),
        entrada("checkout", id_=3, prioridad=3),
    ])

    ctx = await svc.build_context("checkout", max_entries=2)

    assert [e.id for e in ctx.entradas] == [2, 3]


async def test_limite_por_defecto(service):
    # prioridad cicla dentro del rango válido (1..5).
    entradas = [entrada("checkout", id_=i, prioridad=(i % 5) + 1) for i in range(1, 8)]
    svc = service(entradas)

    ctx = await svc.build_context("checkout")

    assert len(ctx.entradas) == MAX_ENTRIES_IN_PROMPT


# ============================================================
# DEGRADACION
# ============================================================

async def test_consulta_vacia_no_consulta_la_tabla(service):
    """Sin consulta no hay nada que matchear; conviene no gastar la lectura."""
    llamadas = []

    svc = KnowledgeAuditService()

    async def _fetch():
        llamadas.append(1)
        return []

    svc._fetch_entries = _fetch

    ctx = await svc.build_context("   ")

    assert ctx.entradas == []
    assert llamadas == []


async def test_tabla_inexistente_degrada_a_contexto_vacio(monkeypatch):
    """El knowledge es opcional: si Supabase falla, el pipeline sigue."""
    svc = KnowledgeAuditService()

    async def _fetch():
        raise RuntimeError("relation knowledge_auditoria does not exist")

    monkeypatch.setattr(svc, "_fetch_entries", _fetch)

    ctx = await svc.build_context("analiza el checkout")

    assert ctx.entradas == []
    assert ctx.como_prompt() == ""


# ============================================================
# RENDERIZADO DEL PROMPT
# ============================================================

def test_como_prompt_incluye_directriz_y_evidencia():
    ctx = KnowledgeContext(
        entradas=[entrada(
            "checkout",
            categoria=KnowledgeCategory.FRICCION,
            directriz="Revisar el flujo de pago.",
            evidencia="URL con mayor afectación.",
            prioridad=1,
        )],
        consulta="analiza el checkout",
    )

    bloque = ctx.como_prompt()

    assert "Revisar el flujo de pago." in bloque
    assert "Evidencia requerida: URL con mayor afectación." in bloque
    assert "friccion" in bloque


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
        entrada("checkout", prioridad=9)


def test_categoria_desconocida_falla_validacion():
    with pytest.raises(ValueError):
        KnowledgeEntry(
            id=1,
            trigger_key="checkout",
            categoria="categoria_inexistente",
            directriz="x",
        )