import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import { useToast } from '../store'
import { Spinner } from '../ui'

// tiny markdown renderer (headings, code, bold, lists)
function md(text: string) {
  const lines = text.split('\n')
  const out: string[] = []
  let inCode = false
  for (const line of lines) {
    if (line.startsWith('```')) { out.push(inCode ? '</code></pre>' : '<pre class="code-editor" style="min-height:auto"><code>'); inCode = !inCode; continue }
    if (inCode) { out.push(line.replace(/</g, '&lt;')); continue }
    let l = line.replace(/</g, '&lt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code class="mono" style="background:var(--bg-2);padding:1px 5px;border-radius:4px">$1</code>')
    if (l.startsWith('# ')) out.push(`<h2>${l.slice(2)}</h2>`)
    else if (l.startsWith('## ')) out.push(`<h3>${l.slice(3)}</h3>`)
    else if (l.startsWith('- ')) out.push(`<li>${l.slice(2)}</li>`)
    else if (l.trim() === '') out.push('<br/>')
    else out.push(`<p>${l}</p>`)
  }
  return out.join('\n')
}

export default function LessonView() {
  const { id } = useParams()
  const nav = useNavigate()
  const { push } = useToast()
  const [lesson, setLesson] = useState<any>(null)
  const [answers, setAnswers] = useState<number[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.get(`/academy/lessons/${id}`).then(l => { setLesson(l); setAnswers(new Array(l.quiz?.length || 0).fill(-1)) }).catch(e => { push(e.message, 'error'); nav('/academy') }) }, [id])
  if (!lesson) return <Spinner />

  const complete = async () => {
    setBusy(true)
    try {
      const body = lesson.quiz ? { quiz_answers: answers } : {}
      const r = await api.post(`/academy/lessons/${id}/complete`, body)
      if (!r.passed) { push(r.message, 'error'); setBusy(false); return }
      // surface ecosystem effects
      const effects = r.effects || []
      const skillUp = effects.flatMap((e: any) => e.skill?.tier_up ? [e.skill.tier_up] : [])
      push(`Lesson complete! ${skillUp.length ? `Skill up: ${skillUp[0]} ⬆` : `+${lesson.xp} XP`}`, 'success')
      nav(`/academy/${lesson.course_slug}`)
    } catch (e: any) { push(e.message, 'error') } finally { setBusy(false) }
  }

  const canSubmit = !lesson.quiz || answers.every(a => a >= 0)

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <Link to={`/academy/${lesson.course_slug}`} className="faint" style={{ fontSize: 13 }}>← Back to course</Link>
      <div className="page-head" style={{ marginTop: 8 }}>
        <h1>{lesson.title}</h1>
        <p>+{lesson.xp} XP {lesson.skill_key && `· grows ${lesson.skill_key}`}</p>
      </div>

      <div className="card">
        {lesson.video_url && (
          <div style={{ marginBottom: 14 }}>
            <a className="btn" href={lesson.video_url} target="_blank" rel="noreferrer">▶ Watch video</a>
          </div>
        )}
        {!lesson.quiz && <div dangerouslySetInnerHTML={{ __html: md(lesson.content) }} />}

        {lesson.quiz && (
          <div>
            <p className="muted">{lesson.content}</p>
            {lesson.quiz.map((item: any, qi: number) => (
              <div key={qi} className="card" style={{ background: 'var(--bg-2)', marginBottom: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 10 }}>{qi + 1}. {item.q}</div>
                {item.options.map((opt: string, oi: number) => (
                  <label key={oi} className="row" style={{ padding: '7px 4px', cursor: 'pointer' }}>
                    <input type="radio" name={`q${qi}`} checked={answers[qi] === oi}
                      onChange={() => setAnswers(a => { const n = [...a]; n[qi] = oi; return n })} />
                    <span>{opt}</span>
                  </label>
                ))}
              </div>
            ))}
            <p className="faint" style={{ fontSize: 13 }}>You need {lesson.pass_score}% to pass.</p>
          </div>
        )}
      </div>

      <div className="row" style={{ marginTop: 16, justifyContent: 'flex-end' }}>
        <button className="btn primary" onClick={complete} disabled={busy || !canSubmit}>
          {lesson.completed ? 'Mark complete again' : lesson.quiz ? 'Submit quiz' : 'Complete lesson'}
        </button>
      </div>
    </div>
  )
}
