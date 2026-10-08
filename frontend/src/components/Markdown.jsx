// Renderizador mínimo de markdown para los mensajes del bot.
//
// El backend devuelve texto con formato (negritas `**`, énfasis `_*`, encabezados
// `###`, listas y bloques de código ```json) y sin procesarlo el usuario ve
// asteriscos crudos. Sin dependencias: solo convierte el subconjunto que Nexo IA
// emite, con salida siempre como texto plano (sin HTML sin escapar).

function inlineNodes(text, keyBase = 0) {
  const nodes = [];
  const re = /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`]+`)/g;
  let last = 0;
  let m;
  let k = keyBase;

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**") || tok.startsWith("__")) {
      nodes.push(<strong key={k++}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith("`")) {
      nodes.push(<code key={k++}>{tok.slice(1, -1)}</code>);
    } else {
      nodes.push(<em key={k++}>{tok.slice(1, -1)}</em>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

const UND_LIST_RE = /^\s*[-*]\s+(.*)$/;
const ORD_LIST_RE = /^\s*\d+[.)]\s+(.*)$/;
const HEADING_RE = /^(#{1,4})\s+(.*)$/;
const FENCE_RE = /^```(\w*)/;

export default function Markdown({ text }) {
  if (!text) return null;

  const lines = String(text).split(/\r?\n/);
  const children = [];
  let list = [];
  let listOrdered = false;

  const flushList = () => {
    if (!list.length) return;
    const Tag = listOrdered ? "ol" : "ul";
    children.push(
      <Tag key={children.length} className="md-list">
        {list.map((item, idx) => (
          <li key={idx}>{inlineNodes(item)}</li>
        ))}
      </Tag>
    );
    list = [];
  };

  let i = 0;
  while (i < lines.length) {
    const raw = lines[i].trimEnd();
    i++;

    if (!raw.trim()) {
      flushList();
      continue;
    }

    const fence = raw.match(FENCE_RE);
    if (fence) {
      flushList();
      const buf = [];
      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        buf.push(lines[i]);
        i++;
      }
      i++; // salto el cierre
      children.push(
        <pre key={children.length} className="md-codeblock">
          <code>{buf.join("\n")}</code>
        </pre>
      );
      continue;
    }

    const heading = raw.match(HEADING_RE);
    if (heading) {
      flushList();
      const level = Math.min(heading[1].length, 4);
      const cls = level >= 4 ? "md-heading md-h4" : "md-heading md-h3";
      children.push(
        <div key={children.length} className={cls}>
          {inlineNodes(heading[2])}
        </div>
      );
      continue;
    }

    const unordered = raw.match(UND_LIST_RE);
    const ordered = raw.match(ORD_LIST_RE);
    if (unordered || ordered) {
      const nextOrdered = Boolean(ordered);
      if (list.length && listOrdered !== nextOrdered) flushList();
      listOrdered = nextOrdered;
      list.push((ordered ? ordered[1] : unordered[1]).trim());
      continue;
    }

    // Párrafo: agrupo líneas consecutivas sin formato de bloque.
    flushList();
    const buf = [raw.trim()];
    while (i < lines.length) {
      const peek = lines[i].trimEnd();
      if (
        !peek.trim() ||
        FENCE_RE.test(peek) ||
        HEADING_RE.test(peek) ||
        UND_LIST_RE.test(peek) ||
        ORD_LIST_RE.test(peek)
      ) {
        break;
      }
      buf.push(peek.trim());
      i++;
    }
    children.push(
      <p key={children.length} className="md-paragraph">
        {buf.map((para, idx) => (
          <span key={idx}>
            {idx > 0 && <br />}
            {inlineNodes(para)}
          </span>
        ))}
      </p>
    );
  }
  flushList();

  return <div className="md-root">{children}</div>;
}