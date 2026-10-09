import zlib

def create_pdf(filename, title, lines):
    # PDF specification 1.4 minimal generator
    objects = []
    
    def add_object(content):
        objects.append(content)
        return len(objects)

    # 1: Catalog
    # 2: Pages
    # 3: Page
    # 4: Font
    # 5: Contents
    
    # We will build text stream
    stream_lines = []
    stream_lines.append("BT")
    stream_lines.append("/F1 18 Tf")
    stream_lines.append("50 750 Td")
    stream_lines.append(f"({escape_pdf(title)}) Tj")
    
    stream_lines.append("/F1 10 Tf")
    stream_lines.append("0 -30 Td")
    
    for line in lines:
        if line.startswith("### "):
            stream_lines.append("/F1 13 Tf")
            stream_lines.append("0 -22 Td")
            stream_lines.append(f"({escape_pdf(line[4:])}) Tj")
            stream_lines.append("/F1 10 Tf")
            stream_lines.append("0 -15 Td")
        elif line.startswith("## "):
            stream_lines.append("/F1 14 Tf")
            stream_lines.append("0 -26 Td")
            stream_lines.append(f"({escape_pdf(line[3:])}) Tj")
            stream_lines.append("/F1 10 Tf")
            stream_lines.append("0 -16 Td")
        elif line.startswith("# "):
            stream_lines.append("/F1 16 Tf")
            stream_lines.append("0 -28 Td")
            stream_lines.append(f"({escape_pdf(line[2:])}) Tj")
            stream_lines.append("/F1 10 Tf")
            stream_lines.append("0 -18 Td")
        elif not line.strip():
            stream_lines.append("0 -10 Td")
        else:
            # Normal line (split into chunks if long)
            chunks = wrap_text(line, 85)
            for chunk in chunks:
                stream_lines.append(f"({escape_pdf(chunk)}) Tj")
                stream_lines.append("0 -13 Td")

    stream_lines.append("ET")
    content_stream = "\n".join(stream_lines).encode("latin1", errors="replace")

    # Objects definition
    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    obj4 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    obj5 = f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin1") + content_stream + b"\nendstream"

    objs = [obj1, obj2, obj3, obj4, obj5]
    
    output = bytearray()
    output.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(output))
        output.extend(f"{i} 0 obj\n".encode("latin1"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
        
    xref_pos = len(output)
    output.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("latin1"))
    for off in offsets:
        output.extend(f"{off:010d} 00000 n \n".encode("latin1"))
        
    output.extend(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin1"))
    
    with open(filename, "wb") as f:
        f.write(output)
    print(f"Generated PDF: {filename} ({len(output)} bytes)")

def escape_pdf(text):
    clean = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # Map common accents to ASCII/Latin1 compatible
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "«": "\"", "»": "\"", "—": "-"
    }
    for k, v in replacements.items():
        clean = clean.replace(k, v)
    return clean

def wrap_text(text, max_len=85):
    words = text.split(" ")
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 > max_len:
            lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
        else:
            curr.append(w)
            curr_len += len(w) + 1
    if curr:
        lines.append(" ".join(curr))
    return lines

if __name__ == "__main__":
    title = "INFORME TECNICO MINSALUD - CAPACIDAD HOSPITALARIA Y AUDITORIA IPS 2026"
    lines = [
        "Republica de Colombia - Ministerio de Salud y Proteccion Social",
        "Direccion de Prestacion de Servicios y Atencion Primaria",
        "",
        "## 1. RESUMEN EJECUTIVO",
        "El presente informe consolida el estado de la infraestructura hospitalaria y capacidad instalada",
        "en Colombia a partir de las auditorias del Registro Especial de Prestadores de Servicios de Salud (REPS).",
        "El analisis evalua la distribucion geografica de camas UCI, servicios criticos y niveles de atencion.",
        "",
        "## 2. DATOS CUANTITATIVOS Y CIFRAS CLAVE AUDITADAS",
        "- Total de prestadores evaluados en la muestra de alta resolucion: 41,427 sedes a nivel nacional.",
        "- Camas de Cuidado Intensivo Adultos (UCI) concentradas: Bogota (1,840 camas), Antioquia (1,410 camas),",
        "  Valle del Cauca (1,150 camas), Atlantico (620 camas) y Santander (510 camas).",
        "- En el departamento de Caldas, el Hospital Departamental Santa Sofia dispone de 184 camas hospitalarias",
        "  y 28 camas UCI adultos habilitadas, mientras que el Hospital Universitario de Caldas cuenta con 210 camas",
        "  de hospitalizacion y 32 camas UCI de alta complejidad.",
        "- La tasa de ocupacion promedio proyectada para el tercer trimestre es del 78.4% en la red publica.",
        "",
        "## 3. CONCLUSIONES Y DIRECTRICES OPERATIVAS",
        "- Se identifica una brecha de cobertura en municipios de categoria 5 y 6 que dependen de E.S.E. de Nivel 1.",
        "- Se ordena priorizar la interoperabilidad digital de historias clinicas y la telemedicina en zonas rurales.",
        "- Toda entidad publica debera reportar mensualmente novedades en quirofanos y servicios quirurgicos habilitados.",
        "",
        "## 4. PREGUNTAS DE CONTROL Y VALIDACION PARA AUDITORIA (Q&A)",
        "P1: Cual es la capacidad de camas UCI del Hospital Universitario de Caldas?",
        "R: El documento certifica 32 camas UCI adultos y 210 camas de hospitalizacion general.",
        "P2: Que departamentos lideran la concentracion de camas criticas?",
        "R: Bogota D.C., Antioquia y Valle del Cauca agrupan mas del 50% de la capacidad nacional.",
        "P3: Pregunta de control fuera de dominio: A que distancia esta Jupiter del Sol?",
        "R: El documento NO contiene informacion astronomica o sobre el sistema solar (debe ser rechazada)."
    ]
    create_pdf("simulacion_documento_jurado_ips.pdf", title, lines)
