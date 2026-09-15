import { useMemo, useRef } from 'react'

// Minimal, dependency-free Python syntax highlighter. Runs entirely inline so it works inside
// the sandboxed preview iframe (no external CDN/highlight.js). It tokenises the source and emits
// coloured spans; a transparent <textarea> sits on top of the highlighted <pre> so the caret,
// selection and typing behaviour are the browser's native ones — we only paint colour underneath.

const KEYWORDS = new Set([
  'def', 'return', 'if', 'elif', 'else', 'for', 'while', 'in', 'not', 'and', 'or',
  'import', 'from', 'as', 'class', 'try', 'except', 'finally', 'raise', 'with',
  'lambda', 'yield', 'pass', 'break', 'continue', 'global', 'nonlocal', 'assert',
  'True', 'False', 'None', 'is', 'del', 'async', 'await',
])
const BUILTINS = new Set([
  'print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'set', 'tuple',
  'sum', 'min', 'max', 'abs', 'sorted', 'enumerate', 'zip', 'map', 'filter', 'bool',
  'round', 'any', 'all', 'reversed', 'isinstance', 'type',
])

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlight(src: string): string {
  // Token regex: comments, strings, numbers, identifiers, everything else (char-by-char).
  const re = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b\d+\.?\d*\b)|([A-Za-z_]\w*)|(\s+)|([^\sA-Za-z_])/g
  let out = ''
  let m: RegExpExecArray | null
  while ((m = re.exec(src)) !== null) {
    const [, comment, string, num, ident, ws, other] = m
    if (comment) out += `<span class="tk-com">${escapeHtml(comment)}</span>`
    else if (string) out += `<span class="tk-str">${escapeHtml(string)}</span>`
    else if (num) out += `<span class="tk-num">${escapeHtml(num)}</span>`
    else if (ident) {
      if (KEYWORDS.has(ident)) out += `<span class="tk-kw">${ident}</span>`
      else if (BUILTINS.has(ident)) out += `<span class="tk-bi">${ident}</span>`
      else out += escapeHtml(ident)
    } else if (ws) out += escapeHtml(ws)
    else out += escapeHtml(other)
  }
  return out
}

export default function CodeEditor({ value, onChange, minHeight = 340 }:
  { value: string; onChange: (v: string) => void; minHeight?: number }) {
  const taRef = useRef<HTMLTextAreaElement>(null)
  const preRef = useRef<HTMLPreElement>(null)

  const lineCount = useMemo(() => Math.max(1, value.split('\n').length), [value])
  const html = useMemo(() => highlight(value) + '\n', [value])

  const syncScroll = () => {
    if (preRef.current && taRef.current) {
      preRef.current.scrollTop = taRef.current.scrollTop
      preRef.current.scrollLeft = taRef.current.scrollLeft
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Tab inserts 4 spaces instead of moving focus.
    if (e.key === 'Tab') {
      e.preventDefault()
      const ta = e.currentTarget
      const s = ta.selectionStart, en = ta.selectionEnd
      const next = value.slice(0, s) + '    ' + value.slice(en)
      onChange(next)
      requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = s + 4 })
    }
  }

  return (
    <div className="ce-wrap" style={{ minHeight }}>
      <div className="ce-gutter" aria-hidden>
        {Array.from({ length: lineCount }, (_, i) => <div key={i}>{i + 1}</div>)}
      </div>
      <div className="ce-code">
        <pre ref={preRef} className="ce-pre" aria-hidden
             dangerouslySetInnerHTML={{ __html: html }} />
        <textarea
          ref={taRef}
          className="ce-ta"
          value={value}
          onChange={e => onChange(e.target.value)}
          onScroll={syncScroll}
          onKeyDown={onKeyDown}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          wrap="off"
        />
      </div>
    </div>
  )
}
