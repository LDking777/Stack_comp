"""
Fuente de datos unica: datos.gov.co (Socrata SODA / SoQL).

Dataset s2ru-bqt6 — "Relación de IPS públicas y privadas según el nivel de
atención y capacidad instalada" (MinSalud/REPS). Toda agregacion (conteos,
sumas de capacidad, agrupaciones) la ejecuta Socrata via SoQL: el LLM nunca
calcula numeros, solo narra.

NUNCA usar api/v3/views/s2ru-bqt6/query.json: ignora $limit y devuelve el
dataset completo (~36 MB). El endpoint /resource/ si respeta filtros y
agregaciones y responde en KB.

La fuente esta congelada desde 2022-11-21, por eso el cache en memoria.
"""
import time
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings
from backend.services.normalization import (
    fold,
    normalize_departamento,
    normalize_grupo_capacidad,
    normalize_naturaleza,
    normalize_nivel_atencion,
    normalize_descripcion_capacidad,
)

logger = logging.getLogger(__name__)

# Columnas fijas del dataset
CAPACITY_COLUMN = "num_cantidad_capacidad_instalada"
GROUP_CAPACITY_COLUMN = "nom_grupo_capacidad"
PRESTADOR_COLUMN = "c_digo_prestador"
IDENTIFIER_FILTER_COLUMNS = frozenset(
    {"nit_ips", PRESTADOR_COLUMN, "nombre_prestador"}
)
ANALYTIC_COLUMNS = frozenset({
    "departamento",
    "municipio",
    "naturaleza",
    "num_nivel_atencion",
    "nom_grupo_capacidad",
    "nom_descripcion_capacidad",
})
FILTER_COLUMNS = ANALYTIC_COLUMNS | IDENTIFIER_FILTER_COLUMNS
ANALYTIC_RECORD_COLUMNS = (
    "departamento",
    "municipio",
    "naturaleza",
    "num_nivel_atencion",
    "nom_grupo_capacidad",
    "nom_descripcion_capacidad",
    CAPACITY_COLUMN,
)
IPS_DIRECTORY_COLUMNS = (
    "c_digo_prestador",
    "c_digo_sede",
    "nombre_prestador",
    "nom_sede_ips",
    "direcci_n",
    "municipio",
    "departamento",
    "naturaleza",
    "num_nivel_atencion",
    "nom_grupo_capacidad",
    "nom_descripcion_capacidad",
)

# Operaciones deterministas que el servicio sabe ejecutar.
OPERATIONS = (
    "count_registros",
    "count_prestadores",
    "group_count",
    "sum_capacity",
    "math",
    "list_distinct",
    "list_ips",
)

_MODE = "agregacion_determinista_socrata"

# Canonizacion de filtros ANTES de armar el $where: el valor del usuario
# ("bogota", "publica") nunca llega crudo a SoQL, que compara exacto y sin
# acentos-insensitive.
_FILTER_NORMALIZERS = {
    "departamento": normalize_departamento,
    "naturaleza": normalize_naturaleza,
    "num_nivel_atencion": normalize_nivel_atencion,
    "nom_grupo_capacidad": normalize_grupo_capacidad,
    "nom_descripcion_capacidad": normalize_descripcion_capacidad,
}
_CACHE_TTL_S = 600.0
_MUNICIPIOS_TTL_S = 86400.0

# Cache generica de respuestas: clave -> (monotonic_ts, valor)
_CACHE: Dict[str, tuple] = {}

# Indice de municipios (fold -> valor exacto del dataset). Los municipios
# llegan en MAYUSCULAS ("APARTADÓ"), asi que sin este indice el filtro
# insensible a acentos/case devolveria 0 filas.
_MUNICIPIOS: Dict[str, str] = {}
_MUNICIPIOS_TS = 0.0
_PRESTADOR_NAMES: List[str] = []
_PRESTADOR_NAMES_TS = 0.0
_MUNICIPIO_DEPARTMENTS: Dict[str, List[tuple[str, str]]] = {}


def _normalize_identifier_filter(column: str, value: Any) -> Optional[str]:
    """Normalize public numeric identifiers to the representation in Socrata."""
    if value is None:
        return None
    text = str(value).strip()
    if column in {"nit_ips", PRESTADOR_COLUMN}:
        digits = re.sub(r"\D", "", text)
        if not 6 <= len(digits) <= 15:
            return None
        if column == "nit_ips" and len(digits) == 10:
            digits = digits[:-1]
        return digits
    return text[:160] or None


def build_where(filters: Optional[Dict[str, Any]]) -> str:
    """Arma la clausula $where de SoQL escapando comillas simples."""
    clauses = []
    for column, value in (filters or {}).items():
        if value is None or str(value).strip() == "":
            continue
        escaped = str(value).replace("'", "''")
        clauses.append(f"{column}='{escaped}'")
    return " AND ".join(clauses)


def normalize_filters(filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Canoniza el valor del usuario ("bogota", "publica") al valor EXACTO del
    dataset antes de armar el $where: SoQL compara literal y su lower() no
    elimina acentos, asi que sin esto el filtro devolveria 0 filas en silencio.
    """
    normalized = {k: v for k, v in (filters or {}).items()}
    for column, normalizer in _FILTER_NORMALIZERS.items():
        if column in normalized:
            normalized[column] = normalizer(normalized[column])
    return normalized


def _parse_number(value: Any) -> Any:
    """SoQL devuelve numeros como strings ("97036"); aqui se pasan a int/float."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        number = float(text)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def _cache_get(key: str, ttl: float) -> Any:
    entry = _CACHE.get(key)
    if entry and (time.monotonic() - entry[0]) < ttl:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    if len(_CACHE) > 512:
        _CACHE.clear()
    _CACHE[key] = (time.monotonic(), value)


class DatosGovService:
    """
    Cliente asíncrono de la API pública de datos.gov.co con agregaciones SoQL.
    """

    def __init__(self):
        self.resource_url = settings.DATOS_GOV_RESOURCE_URL
        self.timeout_s = 10.0

    # ── Metodos publicos ─────────────────────────────────────────────

    async def execute(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una operacion determinista.

        spec:
            operation: una de OPERATIONS.
            filters: {columna: valor_canonico} (departamento, municipio,
                naturaleza, num_nivel_atencion, nom_grupo_capacidad).
            group_by: columna para group_count / sum_capacity agrupado.
            math_operation: sum|avg|min|max (para math / sum_capacity).
            metric: columna numerica (por defecto num_cantidad_capacidad_instalada).
            limit: tope de filas en agrupaciones.
        """
        operation = spec.get("operation") or "count_registros"
        if operation not in OPERATIONS:
            return {
                "error": f"operacion_desconocida: {operation}",
                "status": "sin_datos",
                "modo": _MODE,
            }

        filters = normalize_filters(spec.get("filters") or {})
        invalid_filters = set(filters) - FILTER_COLUMNS
        group_by = spec.get("group_by")
        metric = spec.get("metric") or CAPACITY_COLUMN
        if invalid_filters:
            return self._unsupported_query(
                "Filtro no permitido. Solo se aceptan dimensiones analíticas y "
                "NIT, código o nombre de prestador como filtros internos."
            )
        if group_by and group_by not in ANALYTIC_COLUMNS:
            return self._unsupported_query(
                "Solo se permiten desgloses agregados por ubicación, naturaleza, "
                "nivel y tipo de capacidad."
            )
        if metric != CAPACITY_COLUMN:
            return self._unsupported_query(
                "La única métrica numérica disponible es la cantidad de capacidad instalada."
            )

        for column in IDENTIFIER_FILTER_COLUMNS:
            if column not in filters:
                continue
            normalized_value = _normalize_identifier_filter(column, filters[column])
            if normalized_value is None:
                return self._unsupported_query(
                    "El identificador proporcionado no tiene un formato válido."
                )
            filters[column] = normalized_value

        if filters.get("nombre_prestador"):
            resolved_name, ambiguous_name = await self._resolve_prestador_name(
                filters["nombre_prestador"]
            )
            if ambiguous_name:
                return {
                    "status": "filtro_ambiguo",
                    "detalle": (
                        "El nombre coincide con más de un prestador. "
                        "Usa el nombre completo, NIT o código para precisar la consulta."
                    ),
                    "modo": _MODE,
                }
            if resolved_name is None:
                return {
                    "status": "sin_coincidencias",
                    "detalle": "No encontré coincidencias para el prestador indicado.",
                    "modo": _MODE,
                }
            filters["nombre_prestador"] = resolved_name

        # Los municipios llegan en MAYUSCULAS y con acentos propios: se
        # resuelven contra el indice dinamico del dataset.
        if filters.get("municipio"):
            resolved = await self._resolve_municipio(filters["municipio"])
            if resolved is None:
                return {
                    "status": "sin_coincidencias",
                    "filtros_aplicados": filters,
                    "detalle": (
                        f"No encontre municipios que coincidan con "
                        f"'{filters['municipio']}' en el dataset."
                    ),
                    "modo": _MODE,
                }
            filters["municipio"] = resolved

        where = build_where(filters)
        clean_filters = {k: v for k, v in filters.items() if v}
        public_filters = {
            key: value for key, value in clean_filters.items()
            if key in ANALYTIC_COLUMNS
        }

        try:
            if operation == "list_ips":
                return await self._list_ips(
                    where, public_filters, limit=int(spec.get("limit") or 50)
                )

            if operation == "count_registros":
                return await self._scalar(operation, "count(*)", where, public_filters, "total_registros")

            if operation == "count_prestadores":
                return await self._scalar(
                    operation, f"count(distinct {PRESTADOR_COLUMN})", where,
                    public_filters, "total_prestadores",
                )

            if operation == "group_count":
                return await self._grouped(
                    spec, where, public_filters,
                    aggregate="count(*)", value_key="registros",
                )

            if operation == "sum_capacity":
                metric = spec.get("metric") or CAPACITY_COLUMN
                # Sin group_by la consulta es un total (ej. "cuántas camas
                # hay en Antioquia"): se resuelve como escalar, no como grupo.
                if not spec.get("group_by"):
                    return await self._scalar(
                        operation, f"sum({metric})", where,
                        public_filters, "total_capacidad",
                    )
                return await self._grouped(
                    spec, where, public_filters,
                    aggregate=f"sum({metric})",
                    value_key="capacidad",
                    grouped_key="total_capacidad",
                )

            if operation == "math":
                return await self._math(spec, where, public_filters)

            if operation == "list_distinct":
                return await self._list_distinct(spec, where, public_filters)

        except Exception as e:
            logger.error("Fallo de datos.gov.co en %s: %s", operation, e)
            return {
                "error": f"fuente_publica_no_disponible: {type(e).__name__}",
                "status": "sin_datos",
                "filtros_aplicados": public_filters,
                "modo": _MODE,
                "detalle": (
                    "La API de datos.gov.co no respondio. Los numeros no se "
                    "rellenan con el LLM: reintenta en unos segundos."
                ),
            }

        return {"error": "operacion_no_implementada", "status": "sin_datos"}

    async def fetch_records(
        self, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filas crudas para contexto TOON y para el dashboard. Nunca lanza:
        ante un fallo devuelve lista vacia y el pipeline sigue sin contexto.
        """
        where = build_where(normalize_filters(filters))
        key = f"records|{where}|{limit}"
        cached = _cache_get(key, _CACHE_TTL_S)
        if cached is not None:
            return cached

        params: Dict[str, Any] = {
            "$select": ",".join(ANALYTIC_RECORD_COLUMNS),
            "$limit": limit,
        }
        if where:
            params["$where"] = where

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(self.resource_url, params=params)
                response.raise_for_status()
                rows = response.json()
            _cache_set(key, rows)
            return rows
        except Exception as e:
            logger.warning("No se pudieron leer registros de datos.gov.co: %s", e)
            return []

    @staticmethod
    def dataset_info() -> Dict[str, Any]:
        """Metadatos fijos de la fuente, para GET /api/v1/health."""
        return {
            "dataset_id": "s2ru-bqt6",
            "nombre": "Relación de IPS públicas y privadas según el nivel de atención y capacidad instalada",
            "fuente": "datos.gov.co (Socrata SoQL)",
            "recurso": settings.DATOS_GOV_RESOURCE_URL,
            "data_updated_at": "2022-11-21",
            "filas_conocidas": 41427,
            "nota": (
                "Agregaciones ejecutadas por Socrata via SoQL; el LLM solo "
                "narra. Análisis agregado por ubicación, naturaleza, nivel de "
                "atención, grupo y descripción de capacidad. El directorio "
                "muestra nombre/sede/dirección publicados, nunca NIT o códigos. "
                "Fuente con corte 2022-11-21."
            ),
        }

    @staticmethod
    def _unsupported_query(detail: str) -> Dict[str, Any]:
        return {
            "error": "consulta_no_permitida",
            "status": "sin_datos",
            "detalle": detail,
            "modo": _MODE,
        }

    # ── Internos ─────────────────────────────────────────────────────

    async def _query(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = "q|" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = _cache_get(key, _CACHE_TTL_S)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.get(self.resource_url, params=params)
            response.raise_for_status()
            rows = response.json()

        _cache_set(key, rows)
        return rows

    async def _scalar(
        self, operation: str, select: str, where: str,
        filters: Dict[str, Any], result_key: str,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"$select": select}
        if where:
            params["$where"] = where
        rows = await self._query(params)
        raw = next(iter(rows[0].values()), 0) if rows else 0
        return {
            result_key: _parse_number(raw),
            "filtros_aplicados": filters,
            "modo": _MODE,
        }

    async def _grouped(
        self, spec: Dict[str, Any], where: str, filters: Dict[str, Any],
        aggregate: str, value_key: str, grouped_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        group_by = spec.get("group_by")
        if not group_by:
            return {
                "error": "falta_group_by",
                "status": "sin_datos",
                "filtros_aplicados": filters,
                "modo": _MODE,
            }

        limit = int(spec.get("limit") or 50)
        params: Dict[str, Any] = {
            "$select": f"{group_by},{aggregate}",
            "$group": group_by,
            "$order": "count(*) DESC" if aggregate.startswith("count") else f"{aggregate} DESC",
            "$limit": limit,
        }
        if where:
            params["$where"] = where

        rows = await self._query(params)
        grupos = []
        for row in rows:
            # La clave del agregado varia: "count", "sum_num_cantidad..."
            agg_value = next(
                (v for k, v in row.items() if k != group_by), 0
            )
            grupos.append({
                "valor": row.get(group_by),
                value_key: _parse_number(agg_value),
            })

        result: Dict[str, Any] = {
            "grupo_por": group_by,
            "grupos": grupos,
            "total_grupos": len(grupos),
            "filtros_aplicados": filters,
            "modo": _MODE,
        }
        if grouped_key and aggregate.startswith("sum"):
            # Suma global adicional (sin $group) para poder responder
            # "total de capacidad" junto al desglose.
            total_params: Dict[str, Any] = {"$select": aggregate}
            if where:
                total_params["$where"] = where
            total_rows = await self._query(total_params)
            raw_total = next(iter(total_rows[0].values()), 0) if total_rows else 0
            result[grouped_key] = _parse_number(raw_total)
        return result

    async def _math(
        self, spec: Dict[str, Any], where: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        operation = spec.get("math_operation") or "avg"
        metric = spec.get("metric") or CAPACITY_COLUMN
        if operation not in ("sum", "avg", "min", "max"):
            operation = "avg"

        params: Dict[str, Any] = {"$select": f"{operation}({metric})"}
        if where:
            params["$where"] = where
        rows = await self._query(params)
        raw = next(iter(rows[0].values()), 0) if rows else 0
        value = _parse_number(raw)
        return {
            "operacion": operation,
            "metrica": metric,
            "valor": round(value, 2) if isinstance(value, float) else value,
            "filtros_aplicados": filters,
            "modo": _MODE,
        }

    async def _list_distinct(
        self, spec: Dict[str, Any], where: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        column = spec.get("group_by") or "departamento"
        limit = int(spec.get("limit") or 50)
        params: Dict[str, Any] = {
            "$select": f"{column},count(*)",
            "$group": column,
            "$order": "count(*) DESC",
            "$limit": limit,
        }
        if where:
            params["$where"] = where

        rows = await self._query(params)
        counts: Dict[str, int] = {}
        total = 0
        for row in rows:
            value = str(row.get(column) or "").strip()
            if not value or value.lower() in {"none", "null"}:
                continue
            count = int(_parse_number(next((v for k, v in row.items() if k != column), 0)) or 0)
            counts[value] = counts.get(value, 0) + count
            total += count

        ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "categoria": column,
            "total_valores": len(ordered),
            "valores_distintos": ", ".join(f"{name} ({n})" for name, n in ordered),
            "total_registros": total,
            "filtros_aplicados": filters,
            "modo": _MODE,
        }

    async def _resolve_municipio(self, value: str) -> Optional[str]:
        """
        Devuelve el valor EXACTO del dataset para un municipio (fold -> valor),
        o None si no existe. El indice se refresca cada 24h; el dataset esta
        congelado, asi que en la practica se carga una vez.
        """
        global _MUNICIPIOS_TS
        folded = fold(value)
        if not folded:
            return None

        if not _MUNICIPIOS or (time.monotonic() - _MUNICIPIOS_TS) > _MUNICIPIOS_TTL_S:
            try:
                rows = await self._query({
                    "$select": "municipio,count(*)",
                    "$group": "municipio",
                    "$limit": 3000,
                })
                _MUNICIPIOS.clear()
                for row in rows:
                    name = str(row.get("municipio") or "").strip()
                    if name:
                        _MUNICIPIOS[fold(name)] = name
                _MUNICIPIOS_TS = time.monotonic()
                logger.info("Indice de municipios cargado: %d valores", len(_MUNICIPIOS))
            except Exception as e:
                logger.warning("No se pudo cargar el indice de municipios: %s", e)
                # Sin indice se consulta el valor literal (mejor esfuerzo).
                return value.strip()

        return _MUNICIPIOS.get(folded)

    async def _resolve_prestador_name(
        self, value: str
    ) -> tuple[Optional[str], bool]:
        """Resolve an exact or unique partial name without returning names to users."""
        global _PRESTADOR_NAMES_TS
        folded = fold(value)
        if not folded:
            return None, False

        if (
            not _PRESTADOR_NAMES
            or (time.monotonic() - _PRESTADOR_NAMES_TS) > _MUNICIPIOS_TTL_S
        ):
            rows = await self._query(
                {
                    "$select": "nombre_prestador",
                    "$group": "nombre_prestador",
                    "$limit": 15000,
                }
            )
            _PRESTADOR_NAMES.clear()
            _PRESTADOR_NAMES.extend(
                sorted(
                    {
                        str(row.get("nombre_prestador") or "").strip()
                        for row in rows
                        if row.get("nombre_prestador")
                    }
                )
            )
            _PRESTADOR_NAMES_TS = time.monotonic()

        exact = [name for name in _PRESTADOR_NAMES if fold(name) == folded]
        if len(exact) == 1:
            return exact[0], False
        matches = [name for name in _PRESTADOR_NAMES if folded in fold(name)]
        if len(matches) == 1:
            return matches[0], False
        return None, len(matches) > 1

    async def resolve_municipio_mention(
        self, query: str
    ) -> tuple[Optional[str], Optional[str], bool]:
        """Resolve one municipality in a query, optionally disambiguating by department."""
        global _MUNICIPIOS_TS
        if (
            not _MUNICIPIO_DEPARTMENTS
            or (time.monotonic() - _MUNICIPIOS_TS) > _MUNICIPIOS_TTL_S
        ):
            rows = await self._query(
                {
                    "$select": "municipio,departamento",
                    "$group": "municipio,departamento",
                    "$limit": 5000,
                }
            )
            _MUNICIPIO_DEPARTMENTS.clear()
            for row in rows:
                municipio = str(row.get("municipio") or "").strip()
                departamento = str(row.get("departamento") or "").strip()
                if municipio and departamento:
                    _MUNICIPIO_DEPARTMENTS.setdefault(fold(municipio), []).append(
                        (municipio, departamento)
                    )
            _MUNICIPIOS_TS = time.monotonic()

        folded_query = fold(query)
        municipality_matches = [
            locations
            for folded_name, locations in _MUNICIPIO_DEPARTMENTS.items()
            if re.search(rf"(?<!\w){re.escape(folded_name)}(?!\w)", folded_query)
        ]
        if not municipality_matches:
            return None, None, False

        candidates = [location for locations in municipality_matches for location in locations]
        mentioned_departments = {
            fold(department)
            for locations in _MUNICIPIO_DEPARTMENTS.values()
            for _, department in locations
            if re.search(rf"(?<!\w){re.escape(fold(department))}(?!\w)", folded_query)
        }
        if mentioned_departments:
            candidates = [
                candidate for candidate in candidates
                if fold(candidate[1]) in mentioned_departments
            ]

        unique_candidates = list(dict.fromkeys(candidates))
        if len(unique_candidates) == 1:
            municipio, departamento = unique_candidates[0]
            return municipio, departamento, False
        return None, None, bool(unique_candidates)

    async def _list_ips(
        self, where: str, filters: Dict[str, Any], limit: int = 50
    ) -> Dict[str, Any]:
        """Return public facility directory fields, omitting all provider codes/NIT."""
        group_columns = ",".join(IPS_DIRECTORY_COLUMNS)
        params: Dict[str, Any] = {
            "$select": (
                "c_digo_prestador,c_digo_sede,nombre_prestador,nom_sede_ips,"
                "direcci_n,municipio,departamento,naturaleza,num_nivel_atencion,"
                "nom_grupo_capacidad,nom_descripcion_capacidad,"
                f"sum({CAPACITY_COLUMN}) as capacidad"
            ),
            "$group": group_columns,
            "$order": "nombre_prestador ASC,nom_sede_ips ASC",
            "$limit": 5000,
        }
        if where:
            params["$where"] = where

        rows = await self._query(params)
        facilities: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            facility_key = (
                row.get("c_digo_prestador"),
                row.get("c_digo_sede"),
                row.get("nombre_prestador"),
                row.get("nom_sede_ips"),
                row.get("direcci_n"),
                row.get("municipio"),
                row.get("departamento"),
            )
            facility = facilities.setdefault(
                facility_key,
                {
                    "nombre": row.get("nombre_prestador"),
                    "sede": row.get("nom_sede_ips"),
                    "direccion": row.get("direcci_n"),
                    "municipio": row.get("municipio"),
                    "departamento": row.get("departamento"),
                    "naturaleza": [],
                    "niveles_atencion": [],
                    "capacidades": [],
                },
            )
            for field, value in (
                ("naturaleza", row.get("naturaleza")),
                ("niveles_atencion", row.get("num_nivel_atencion")),
            ):
                if value is not None and value not in facility[field]:
                    facility[field].append(value)
            capacity = {
                "grupo": row.get("nom_grupo_capacidad"),
                "tipo": row.get("nom_descripcion_capacidad"),
                "cantidad": _parse_number(row.get("capacidad")),
            }
            if capacity not in facility["capacidades"]:
                facility["capacidades"].append(capacity)

        compare_capacity = bool(
            {"nom_grupo_capacidad", "nom_descripcion_capacidad"}.intersection(filters)
        )
        ordered_facilities = sorted(
            facilities.values(),
            key=lambda facility: (
                -sum(
                    capacity["cantidad"]
                    for capacity in facility["capacidades"]
                    if isinstance(capacity.get("cantidad"), (int, float))
                )
                if compare_capacity
                else 0,
                str(facility.get("nombre") or ""),
                str(facility.get("sede") or ""),
            ),
        )
        requested_limit = min(max(limit, 1), 100)
        return {
            "establecimientos": ordered_facilities[:requested_limit],
            "total_establecimientos": len(ordered_facilities),
            "resultados_limitados": len(ordered_facilities) > requested_limit,
            "fuente_registros_limitada": len(rows) == 5000,
            "filtros_aplicados": filters,
            "modo": _MODE,
        }


datosgov_service = DatosGovService()
