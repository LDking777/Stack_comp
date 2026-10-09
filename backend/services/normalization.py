"""
Normalizacion de entidades del dataset de IPS (datos.gov.co, id s2ru-bqt6).

La fuente esta congelada desde 2022-11-21, asi que los valores canonicos se
mantienen estaticos aqui. Lo critico: SoQL compara texto EXACTO y su lower()
no elimina acentos ('publica' != 'Pública'), asi que toda la canonizacion
(alias + insensible a acentos y mayusculas) ocurre en este modulo antes de
armar la consulta.
"""
import unicodedata
import logging

logger = logging.getLogger(__name__)


def strip_accents(value: str) -> str:
    """Elimina diacriticos: 'Bogotá' -> 'Bogota', 'Nariño' -> 'Narino'."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", without_marks)


def fold(value) -> str:
    """Version comparable de un valor: sin acentos, minusculas, sin espacios sobrantes."""
    if value is None:
        return ""
    return strip_accents(str(value)).strip().lower()


def _index(values):
    return {fold(v): v for v in values}


# ── Departamentos: valores exactos del dataset (38) ──
# Incluye ciudades que el REPS reporta como entidad propia (Barranquilla,
# Cali, Cartagena, Santa Marta, Buenaventura) y "Valle del cauca" con minuscula.
DEPARTAMENTOS = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Barranquilla",
    "Bogotá D.C", "Bolívar", "Boyacá", "Buenaventura", "Caldas", "Cali",
    "Caquetá", "Cartagena", "Casanare", "Cauca", "Cesar", "Chocó",
    "Córdoba", "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira",
    "Magdalena", "Meta", "Nariño", "Norte de Santander", "Putumayo",
    "Quindío", "Risaralda", "San Andrés y Providencia", "Santa Marta",
    "Santander", "Sucre", "Tolima", "Valle del cauca", "Vaupés", "Vichada",
]
_DEPARTAMENTO_INDEX = _index(DEPARTAMENTOS)

# Alias populares que no coinciden por simple fold ("bogota" != "bogota d.c").
_DEPARTAMENTO_ALIASES = {
    "bogota": "Bogotá D.C",
    "bogota d.c.": "Bogotá D.C",
    "bogota dc": "Bogotá D.C",
    "bta": "Bogotá D.C",
    "capital": "Bogotá D.C",
    "distrito capital": "Bogotá D.C",
    "norte santander": "Norte de Santander",
    "n santander": "Norte de Santander",
    "san andres": "San Andrés y Providencia",
    "archipielago de san andres": "San Andrés y Providencia",
    "guajira": "La Guajira",
    "valle": "Valle del cauca",
}

# Para busqueda por palabra dentro de una consulta (router/fallback):
# clave plegada (sin acentos, minusculas) -> valor canonico del dataset.
DEPARTAMENTO_LOOKUP = {**_DEPARTAMENTO_INDEX, **_DEPARTAMENTO_ALIASES}

# ── Naturaleza juridica de la IPS ──
_NATURALEZA_INDEX = {"publica": "Pública", "privada": "Privada", "mixta": "Mixta"}
_NATURALEZA_ALIASES = {
    "publico": "Pública",
    "publicos": "Pública",
    "estatal": "Pública",
    "estatales": "Pública",
    "gubernamental": "Pública",
    "oficial": "Pública",
    "priv": "Privada",
    "privados": "Privada",
    "particular": "Privada",
}

# ── Nivel de atencion (1 primario, 2 medio, 3 alto) ──
_NIVEL_INDEX = {
    "1": "1", "2": "2", "3": "3",
    "primario": "1", "primaria": "1", "basico": "1", "nivel 1": "1",
    "secundario": "2", "secundaria": "2", "nivel 2": "2",
    "terciario": "3", "terciaria": "3", "alto": "3", "nivel 3": "3",
}

# ── Grupos de capacidad instalada ──
GRUPOS_CAPACIDAD = [
    "CAMAS", "CONSULTORIOS", "SALAS", "AMBULANCIAS", "CAMILLAS",
    "UNIDAD MOVIL", "SILLAS",
]
_GRUPO_INDEX = _index(GRUPOS_CAPACIDAD)
_GRUPO_ALIASES = {
    "cama": "CAMAS",
    "consultorio": "CONSULTORIOS",
    "sala": "SALAS",
    "ambulancia": "AMBULANCIAS",
    "camilla": "CAMILLAS",
    "movil": "UNIDAD MOVIL",
    "silla": "SILLAS",
}
GRUPO_LOOKUP = {**_GRUPO_INDEX, **_GRUPO_ALIASES}

# ── Descripciones de capacidad instaladas (valores reales del dataset) ──
DESCRIPCIONES_CAPACIDAD = [
    "Consulta Externa", "Procedimientos", "Básica", "Adultos", "Urgencias",
    "Observación Adultos Mujeres", "Observación Adultos Hombres",
    "Observación Pediátrica", "Pediátrica", "Medicalizada", "Sala de Cirugía",
    "Partos", "TPR", "Unidad Móvil", "Intermedia Adultos",
    "Intensiva Adultos", "Sillas de Hemodiálisis", "Salud Mental Adulto",
    "Sillas de Quimioterapia", "Incubadora Intensiva Neonatal",
    "Incubadora Intermedia Neonatal", "Salud Mental", "Quirófano",
    "Atención del Parto", "Paciente crónico sin ventilador",
    "Cuna Básico Neonatal", "SPA Básico Adultos", "SPA Adultos", "SPA",
    "Incubadora Básico Neonatal", "Intensiva Pediátrica",
    "Intermedia Pediátrica", "Paciente crónico con ventilador",
    "Salud Mental Pediátrico", "Cuna Intermedia Neonatal",
    "Cuidado Intermedio Adulto", "Cuidado Intensivo Adulto",
    "SPA Pediátricas", "Otras patologías", "SPA Básico Pediátricos",
    "Sala de Radioterapia", "Obstetricia", "Cuidado Intermedio Neonatal",
    "Cuidado básico neonatal", "Cuna Intermedia Pediátrica",
    "Cuidado Intensivo Neonatal", "Cuidado Intermedio Pediátrico",
    "Cuna Intensiva Neonatal", "Cuidado Intensivo Pediátrico",
    "Cuna Intensiva Pediátrica", "Intensiva Quemado Adulto",
    "Farmacodependencia", "Intensiva Quemado pediátrica", "Psiquiatría",
    "Institución Paciente Crónico", "Unidad de Quemados Adulto",
    "Transplante de progenitores hematopoyeticos",
    "Unidad de Quemados Pediátrico", "Cuidado Agudo Mental",
]
_DESCRIPCION_INDEX = _index(DESCRIPCIONES_CAPACIDAD)
_DESCRIPCION_ALIASES = {
    "camas de adultos": "Adultos",
    "cama de adulto": "Adultos",
    "camas pediatricas": "Pediátrica",
    "cama pediatrica": "Pediátrica",
    "observacion pediatrica": "Observación Pediátrica",
    "sala de cirugias": "Sala de Cirugía",
    "salas de cirugia": "Sala de Cirugía",
    "cirugias": "Sala de Cirugía",
    "uci adultos": "Cuidado Intensivo Adulto",
    "uci adulto": "Cuidado Intensivo Adulto",
    "uci pediatrica": "Cuidado Intensivo Pediátrico",
    "uci neonatal": "Cuidado Intensivo Neonatal",
    "hemodialisis": "Sillas de Hemodiálisis",
    "quimioterapia": "Sillas de Quimioterapia",
    "unidad movil": "Unidad Móvil",
    "incubadoras neonatales": "Incubadora Básico Neonatal",
}
DESCRIPCION_CAPACIDAD_LOOKUP = {
    **_DESCRIPCION_INDEX,
    **{fold(alias): canonical for alias, canonical in _DESCRIPCION_ALIASES.items()},
}


def normalize_departamento(value: str | None) -> str | None:
    """
    Devuelve el valor EXACTO del dataset para un departamento.

    Sin alias conocido devuelve la entrada recortada tal cual: la consulta
    SoQL devolveria 0 filas (honesto) en lugar de silenciar el filtro y
    mostrar datos globales. None solo si la entrada esta vacia.
    """
    if value is None:
        return None
    folded = fold(value)
    if not folded:
        return None
    if folded in _DEPARTAMENTO_INDEX:
        return _DEPARTAMENTO_INDEX[folded]
    if folded in _DEPARTAMENTO_ALIASES:
        return _DEPARTAMENTO_ALIASES[folded]
    return str(value).strip()


def normalize_naturaleza(value: str | None) -> str | None:
    """'publico', 'Pública', 'estatal' -> 'Pública'."""
    if value is None:
        return None
    folded = fold(value)
    if not folded:
        return None
    if folded in _NATURALEZA_INDEX:
        return _NATURALEZA_INDEX[folded]
    if folded in _NATURALEZA_ALIASES:
        return _NATURALEZA_ALIASES[folded]
    return str(value).strip()


def normalize_nivel_atencion(value: str | None) -> str | None:
    """'primario', 'nivel 2', '3' -> '1'/'2'/'3' (texto, como en el dataset)."""
    if value is None:
        return None
    folded = fold(value)
    if not folded:
        return None
    return _NIVEL_INDEX.get(folded, str(value).strip())


def normalize_grupo_capacidad(value: str | None) -> str | None:
    """'camas', 'cama', 'CAMAS' -> 'CAMAS' (valor exacto del dataset)."""
    if value is None:
        return None
    folded = fold(value)
    if not folded:
        return None
    if folded in _GRUPO_INDEX:
        return _GRUPO_INDEX[folded]
    if folded in _GRUPO_ALIASES:
        return _GRUPO_ALIASES[folded]
    return str(value).strip()


def normalize_descripcion_capacidad(value: str | None) -> str | None:
    """Normaliza una descripción de capacidad a su valor exacto en Socrata."""
    if value is None:
        return None
    folded = fold(value)
    if not folded:
        return None
    return DESCRIPCION_CAPACIDAD_LOOKUP.get(folded, str(value).strip())


def match_department(value: str, target: str) -> bool:
    """Comparacion insensible a acentos/mayusculas entre dos departamentos."""
    a, b = normalize_departamento(value), normalize_departamento(target)
    if not a or not b:
        return False
    return fold(a) == fold(b)
