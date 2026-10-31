import { ChevronRight, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Textarea } from '@/components/ui/textarea'
import { streamMessage } from '@/lib/api'

const MAX_MESSAGE_CHARS = 8000
// Skills reach the agent as read_skill_file calls (pre-reads included) with args.path = '<name>/SKILL.md'.
const READ_SKILL_FILE = 'read_skill_file'
const SKILL_FILE_SUFFIX = /\/SKILL\.md$/

export interface ToolStep {
  id: string
  name: string
  ok?: boolean
}

export interface Turn {
  id: string
  role: 'user' | 'assistant'
  text: string
  tools: ToolStep[]
  skills: string[]
  error?: string
}

interface Props {
  sessionId: string
  turns: Turn[]
  onTurns: (update: (turns: Turn[]) => Turn[]) => void
  libraryEmpty: boolean
  onTurnEnded: () => void
}

export function Chat({ sessionId, turns, onTurns, libraryEmpty, onTurnEnded }: Props) {
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [turns])

  async function send() {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setBusy(true)
    const answerId = crypto.randomUUID()
    onTurns((t) => [
      ...t,
      { id: crypto.randomUUID(), role: 'user', text, tools: [], skills: [] },
      { id: answerId, role: 'assistant', text: '', tools: [], skills: [] },
    ])
    const patch = (fn: (turn: Turn) => Turn) =>
      onTurns((t) => t.map((x) => (x.id === answerId ? fn(x) : x)))
    try {
      for await (const e of streamMessage(sessionId, text)) {
        if (e.type === 'token') patch((x) => ({ ...x, text: x.text + e.text }))
        else if (e.type === 'tool_start')
          patch((x) => ({
            ...x,
            tools: [...x.tools, { id: e.id, name: e.name }],
            skills: e.name === READ_SKILL_FILE ? addSkill(x.skills, e.args.path) : x.skills,
          }))
        else if (e.type === 'tool_end')
          patch((x) => ({ ...x, tools: x.tools.map((s) => (s.id === e.id ? { ...s, ok: e.ok } : s)) }))
        else if (e.type === 'error') patch((x) => ({ ...x, error: e.message }))
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Connection lost'
      patch((x) => ({ ...x, error: message }))
      toast.error(message)
    } finally {
      setBusy(false)
      onTurnEnded()
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
          {libraryEmpty && (
            <p className="text-sm text-muted-foreground">
              Your library is empty. Upload PDFs in Library to ask questions about them.
            </p>
          )}
          {turns.map((t) =>
            t.role === 'user' ? <UserTurn key={t.id} turn={t} /> : <AnswerTurn key={t.id} turn={t} />,
          )}
          <div ref={bottom} />
        </div>
      </div>
      <div className="border-t p-4">
        <form
          className="mx-auto flex max-w-3xl items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void send()
          }}
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void send()
              }
            }}
            placeholder="Ask about your documents…"
            maxLength={MAX_MESSAGE_CHARS}
            className="max-h-40 min-h-10 resize-none"
            rows={1}
          />
          <Button type="submit" size="icon" disabled={busy || !input.trim()} aria-label="Send">
            <Send />
          </Button>
        </form>
      </div>
    </div>
  )
}

function addSkill(skills: string[], path: unknown): string[] {
  const name = String(path ?? '').trim().replace(SKILL_FILE_SUFFIX, '')
  return !name || skills.includes(name) ? skills : [...skills, name]
}

function UserTurn({ turn }: { turn: Turn }) {
  return (
    <p className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-muted px-3 py-2 text-sm">
      {turn.text}
    </p>
  )
}

function AnswerTurn({ turn }: { turn: Turn }) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      {turn.text && (
        <div className="space-y-3 leading-relaxed [&_a]:underline [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-muted [&_pre]:p-3 [&_ul]:list-disc [&_ul]:pl-5">
          <Markdown skipHtml>{turn.text}</Markdown>
        </div>
      )}
      {turn.error && <p className="text-destructive">{turn.error}</p>}
      {!turn.text && !turn.error && <p className="text-muted-foreground">Thinking…</p>}
      <Steps skills={turn.skills} tools={turn.tools.filter((s) => s.name !== READ_SKILL_FILE)} />
    </div>
  )
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

function Steps({ skills, tools }: { skills: string[]; tools: ToolStep[] }) {
  if (skills.length === 0 && tools.length === 0) return null
  const summary = [
    skills.length > 0 && plural(skills.length, 'skill'),
    tools.length > 0 && plural(tools.length, 'tool'),
  ]
    .filter(Boolean)
    .join(' · ')
  return (
    <Collapsible>
      <CollapsibleTrigger className="group flex items-center gap-1 text-xs text-muted-foreground">
        <ChevronRight className="size-3 transition-transform group-data-[state=open]:rotate-90" />
        {summary}
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1 space-y-0.5 pl-4 text-xs text-muted-foreground">
        {skills.map((name) => (
          <div key={name}>skill: {name}</div>
        ))}
        {tools.map((s) => (
          <div key={s.id}>
            tool: {s.name} {s.ok === undefined ? '…' : s.ok ? '✓' : '✗'}
          </div>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}
