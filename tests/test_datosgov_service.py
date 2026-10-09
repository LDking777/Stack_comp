"""
Pruebas de la capa de datos (datos.gov.co / SoQL).

No llaman a la red: se dobla `DatosGovService._query`, que es el único punto
que habla con la API pública. Lo que importa aquí es que cada operación
determinista arme bien el `$select`/`$where` y traduzca la respuesta.
"""

import pytest

from backend.services import datosgov_service as datosgov_module
from backend.services.datosgov_service import (
    DatosGovService,
    _parse_number,
    build_where,
    normalize_filters,
)


@pytest.fixture(autouse=True)
def _limpiar_cache():
    """Los caches de módulo son globales: sin limpiarlos, un test contamina otro."""
    datosgov_module._CACHE.clear()
    datosgov_module._MUNICIPIOS.clear()
    datosgov_module._MUNICIPIOS_TS = 0.0
    datosgov_module._MUNICIPIO_DEPARTMENTS.clear()
    yield
    datosgov_module._CACHE.clear()


# ============================================================
# HELPERS PUROS
# ============================================================

def test_build_where_escapa_comillas():
    where = build_where({"departamento": "O'Higgins"})
    assert where == "departamento='O''Higgins'"


def test_build_where_ignora_vacios():
    assert build_where({"departamento": None, "municipio": "  "}) == ""
    assert build_where({"departamento": "Antioquia", "municipio": None}) == "departamento='Antioquia'"


def test_normalize_filters_canoniza_al_valor_del_dataset():
    normalized = normalize_filters(
        {
            "departamento": "bogota",
            "naturaleza": "publica",
            "num_nivel_atencion": "nivel 3",
            "nom_grupo_capacidad": "camas",
            "nom_descripcion_capacidad": "camas pediatricas",
        }
    )

    assert normalized["departamento"] == "Bogotá D.C"
    assert normalized["naturaleza"] == "Pública"
    assert normalized["num_nivel_atencion"] == "3"
    assert normalized["nom_grupo_capacidad"] == "CAMAS"
    assert normalized["nom_descripcion_capacidad"] == "Pediátrica"


@pytest.mark.parametrize(
    "raw,expected",
    [("97036", 97036), ("1.5", 1.5), ("2.0", 2), (None, None), ("", 0), (5, 5)],
)
def test_parse_number(raw, expected):
    assert _parse_number(raw) == expected


# ============================================================
# OPERACIONES (con _query doblado)
# ============================================================

@pytest.fixture
def service(monkeypatch):
    """Servicio con `_query` doblado por una respuesta por caso de prueba."""
    svc = DatosGovService()
    respuestas = {}

    async def fake_query(params):
        # Empareja por el `$select` para no depender del orden de las llamadas.
        select = params.get("$select", "")
        for fragmento, rows in respuestas.items():
            if fragmento in select:
                return rows
        return []

    monkeypatch.setattr(svc, "_query", fake_query)

    def _set(fragmento, rows):
        respuestas[fragmento] = rows
        return svc

    return _set


async def test_count_registros(service):
    svc = service("count(*)", [{"count": "41427"}])

    result = await svc.execute({"operation": "count_registros"})

    assert result["total_registros"] == 41427
    assert result["modo"] == "agregacion_determinista_socrata"


async def test_count_prestadores(service):
    svc = service("count(distinct", [{"count_c_digo_prestador": "9320"}])

    result = await svc.execute({"operation": "count_prestadores"})

    assert result["total_prestadores"] == 9320


async def test_group_count(service):
    svc = service("naturaleza,count(*)", [
        {"naturaleza": "Privada", "count": "25067"},
        {"naturaleza": "Pública", "count": "16174"},
    ])

    result = await svc.execute({"operation": "group_count", "group_by": "naturaleza"})

    assert result["grupo_por"] == "naturaleza"
    assert result["grupos"] == [
        {"valor": "Privada", "registros": 25067},
        {"valor": "Pública", "registros": 16174},
    ]


async def test_group_count_sin_group_by_falla_honestamente(service):
    svc = service("count(*)", [{"count": "1"}])

    result = await svc.execute({"operation": "group_count"})

    assert result["status"] == "sin_datos"
    assert result["error"] == "falta_group_by"


async def test_sum_capacity_sin_group_by_es_escalar(service):
    svc = service("sum(", [{"sum_num_cantidad_capacidad_instalada": "97036"}])

    result = await svc.execute(
        {"operation": "sum_capacity", "filters": {"nom_grupo_capacidad": "CAMAS"}}
    )

    assert result["total_capacidad"] == 97036
    assert result["filtros_aplicados"]["nom_grupo_capacidad"] == "CAMAS"


async def test_sum_capacity_por_descripcion(service):
    svc = service("sum(", [{"sum_num_cantidad_capacidad_instalada": "1240"}])

    result = await svc.execute(
        {
            "operation": "sum_capacity",
            "filters": {"nom_descripcion_capacidad": "uci neonatal"},
        }
    )

    assert result["total_capacidad"] == 1240
    assert result["filtros_aplicados"]["nom_descripcion_capacidad"] == (
        "Cuidado Intensivo Neonatal"
    )


@pytest.mark.parametrize(
    "spec",
    [
        {"operation": "group_count", "group_by": "nombre_prestador"},
        {"operation": "list_distinct", "group_by": "nit_ips"},
    ],
)
async def test_rechaza_consultas_con_identificadores(spec, service):
    svc = service("count(*)", [{"count": "1"}])

    result = await svc.execute(spec)

    assert result["status"] == "sin_datos"
    assert result["error"] == "consulta_no_permitida"


async def test_math_avg(service):
    svc = service("avg(", [{"avg_num_cantidad_capacidad_instalada": "5.3"}])

    result = await svc.execute({"operation": "math", "math_operation": "avg"})

    assert result["operacion"] == "avg"
    assert result["valor"] == 5.3


async def test_list_distinct_ordena_por_conteo(service):
    svc = service("count(*)", [
        {"departamento": "Antioquia", "count": "4245"},
        {"departamento": "Bogotá D.C", "count": "4647"},
    ])

    result = await svc.execute({"operation": "list_distinct", "group_by": "departamento"})

    assert result["categoria"] == "departamento"
    assert result["total_valores"] == 2
    assert result["valores_distintos"].startswith("Bogotá D.C (4647)")


async def test_list_ips_deduplica_sede_y_no_expone_identificadores(monkeypatch):
    svc = DatosGovService()
    captured = {}
    rows = [
        {
            "c_digo_prestador": "504512253",
            "c_digo_sede": "123456",
            "nombre_prestador": "Instituto Oftalmológico",
            "nom_sede_ips": "Sede Centro",
            "direcci_n": "Calle 10",
            "tel_fono": "606-123-4567",
            "municipio": "MANIZALES",
            "departamento": "Caldas",
            "naturaleza": "Privada",
            "num_nivel_atencion": "2",
            "nom_grupo_capacidad": "CONSULTORIOS",
            "nom_descripcion_capacidad": "Consulta Externa",
            "capacidad": "4",
            "email": "no-debe-salir@example.com",
            "gerente": "Dato personal",
        },
        {
            "c_digo_prestador": "504512253",
            "c_digo_sede": "123456",
            "nombre_prestador": "Instituto Oftalmológico",
            "nom_sede_ips": "Sede Centro",
            "direcci_n": "Calle 10",
            "municipio": "MANIZALES",
            "departamento": "Caldas",
            "naturaleza": "Privada",
            "num_nivel_atencion": "2",
            "nom_grupo_capacidad": "CONSULTORIOS",
            "nom_descripcion_capacidad": "Procedimientos",
            "capacidad": "2",
            "tel_fono": "606-123-4567",
        },
    ]

    async def fake_query(params):
        captured.update(params)
        return rows

    monkeypatch.setattr(svc, "_query", fake_query)

    result = await svc.execute(
        {
            "operation": "list_ips",
            "filters": {"municipio": "Manizales", "nom_grupo_capacidad": "consultorio"},
        }
    )

    assert result["total_establecimientos"] == 1
    assert len(result["establecimientos"]) == 1
    assert len(result["establecimientos"][0]["capacidades"]) == 2
    assert result["establecimientos"][0]["municipio"] == "MANIZALES"
    assert "c_digo_prestador" not in result["establecimientos"][0]
    assert "c_digo_sede" not in result["establecimientos"][0]
    assert "nit_ips" not in result["establecimientos"][0]
    assert result["establecimientos"][0]["telefonos"] == ["606-123-4567"]
    assert "email" not in result["establecimientos"][0]
    assert "gerente" not in result["establecimientos"][0]
    assert "tel_fono" in captured["$group"].split(",")
    assert "num_cantidad_capacidad_instalada" not in captured["$group"].split(",")
    assert captured["$where"] == "municipio='MANIZALES' AND nom_grupo_capacidad='CONSULTORIOS'"


async def test_resuelve_municipio_explicito_sin_confundir_apartado_de_urgencias(monkeypatch):
    svc = DatosGovService()

    async def fake_query(_params):
        return [
            {"municipio": "MANIZALES", "departamento": "Caldas"},
            {"municipio": "APARTADÓ", "departamento": "Antioquia"},
            {"municipio": "MEDELLÍN", "departamento": "Antioquia"},
        ]

    monkeypatch.setattr(svc, "_query", fake_query)

    assert await svc.resolve_municipio_mention(
        "Necesito en Manizales saber quienes tienen el apartado de urgencias"
    ) == ("MANIZALES", "Caldas", False)
    assert await svc.resolve_municipio_mention(
        "Necesito en Manizales y Medellín saber quienes tienen urgencias"
    ) == (None, None, True)


async def test_list_ips_acepta_nit_como_filtro_interno(service):
    svc = service("sum(num_cantidad_capacidad_instalada)", [])
    captured = {}

    async def fake_query(params):
        captured.update(params)
        return []

    svc._query = fake_query

    result = await svc.execute(
        {"operation": "list_ips", "filters": {"nit_ips": "900.497.151-2"}}
    )

    assert result["total_establecimientos"] == 0
    assert captured["$where"] == "nit_ips='900497151'"


async def test_operacion_desconocida_no_inventa_datos(service):
    svc = service("count(*)", [{"count": "1"}])

    result = await svc.execute({"operation": "no_existe"})

    assert result["status"] == "sin_datos"
    assert "operacion_desconocida" in result["error"]


async def test_sin_datos_marca_error_sin_alucinar(service):
    """Un fallo de red no se rellena con el LLM: se devuelve sin_datos."""
    svc = DatosGovService()

    async def boom(_params):
        raise RuntimeError("timeout")

    svc._query = boom

    result = await svc.execute({"operation": "count_registros"})

    assert result["status"] == "sin_datos"
    assert "fuente_publica_no_disponible" in result["error"]


async def test_fetch_records_solo_solicita_campos_analiticos(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"departamento": "Antioquia"}]

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, params):
            captured.update(params)
            return FakeResponse()

    monkeypatch.setattr(datosgov_module.httpx, "AsyncClient", FakeAsyncClient)

    records = await DatosGovService().fetch_records(limit=1)

    assert records == [{"departamento": "Antioquia"}]
    selected = set(captured["$select"].split(","))
    assert selected == {
        "departamento",
        "municipio",
        "naturaleza",
        "num_nivel_atencion",
        "nom_grupo_capacidad",
        "nom_descripcion_capacidad",
        "num_cantidad_capacidad_instalada",
    }
    assert not selected.intersection(
        {"c_digo_prestador", "nombre_prestador", "nit_ips", "nom_sede_ips"}
    )
