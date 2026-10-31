import { Library as LibraryIcon, MessageSquarePlus, Pencil, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Chat, type Turn } from '@/components/Chat'
import { Library } from '@/components/Library'
import { Button } from '@/components/ui/button'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Toaster } from '@/components/ui/sonner'
import { api, type LibraryDocument, type ModelInfo, type Session } from '@/lib/api'

const POLL_MS = 2000

const errorText = (e: unknown): string => (e instanceof Error ? e.message : 'Request failed')

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [documents, setDocuments] = useState<LibraryDocument[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [view, setView] = useState<'chat' | 'library'>('chat')
  const [turns, setTurns] = useState<Record<string, Turn[]>>({})
  const [models, setModels] = useState<ModelInfo[]>([])
  const [modelId, setModelId] = useState('')

  const refreshSessions = useCallback(
    () => api.listSessions().then(setSessions).catch((e: unknown) => toast.error(errorText(e))),
    [],
  )
  const refreshDocuments = useCallback(
    () => api.listDocuments().then(setDocuments).catch((e: unknown) => toast.error(errorText(e))),
    [],
  )

  useEffect(() => {
    void refreshSessions()
    void refreshDocuments()
    api
      .listModels()
      .then((list) => {
        setModels(list)
        setModelId(list[0]?.id ?? '')
      })
      .catch((e: unknown) => toast.error(errorText(e)))
  }, [refreshSessions, refreshDocuments])

  const anyPending = documents.some((d) => d.status === 'pending')
  useEffect(() => {
    if (!anyPending) return
    const timer = setInterval(() => void refreshDocuments(), POLL_MS)
    return () => clearInterval(timer)
  }, [anyPending, refreshDocuments])

  async function newSession() {
    try {
      const s = await api.createSession()
      setSessions((list) => [s, ...list])
      setActive(s.id)
      setView('chat')
    } catch (e) {
      toast.error(errorText(e))
    }
  }

  async function rename(s: Session) {
    const title = window.prompt('Rename session', s.title)?.trim()
    if (!title || title === s.title) return
    try {
      await api.renameSession(s.id, title)
      await refreshSessions()
    } catch (e) {
      toast.error(errorText(e))
    }
  }

  async function remove(s: Session) {
    if (!window.confirm(`Delete "${s.title}"?`)) return
    try {
      await api.deleteSession(s.id)
      if (active === s.id) setActive(null)
      await refreshSessions()
    } catch (e) {
      toast.error(errorText(e))
    }
  }

  const title =
    view === 'library' ? 'Library' : (sessions.find((s) => s.id === active)?.title ?? 'Agentic RAG')

  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader>
          <Button variant="outline" onClick={() => void newSession()}>
            <MessageSquarePlus /> New session
          </Button>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={view === 'library'} onClick={() => setView('library')}>
                  <LibraryIcon /> Library
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>
          <SidebarGroup>
            <SidebarMenu>
              {sessions.map((s) => (
                <SidebarMenuItem key={s.id}>
                  <SidebarMenuButton
                    isActive={view === 'chat' && active === s.id}
                    onClick={() => {
                      setActive(s.id)
                      setView('chat')
                    }}
                  >
                    <span className="truncate">{s.title}</span>
                  </SidebarMenuButton>
                  <SidebarMenuAction className="right-8" aria-label="Rename" onClick={() => void rename(s)}>
                    <Pencil />
                  </SidebarMenuAction>
                  <SidebarMenuAction aria-label="Delete" onClick={() => void remove(s)}>
                    <Trash2 />
                  </SidebarMenuAction>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>
      </Sidebar>
      <SidebarInset className="h-svh">
        <header className="flex h-12 items-center gap-2 border-b px-3">
          <SidebarTrigger />
          <span className="text-sm font-medium">{title}</span>
        </header>
        <div className="min-h-0 flex-1 overflow-auto">
          {view === 'library' ? (
            <Library documents={documents} onChanged={() => void refreshDocuments()} />
          ) : active ? (
            <Chat
              key={active}
              sessionId={active}
              turns={turns[active] ?? []}
              onTurns={(fn) => setTurns((all) => ({ ...all, [active]: fn(all[active] ?? []) }))}
              libraryEmpty={documents.length === 0}
              models={models}
              modelId={modelId}
              onModelChange={setModelId}
              onTurnEnded={() => void refreshSessions()}
            />
          ) : (
            <p className="p-6 text-sm text-muted-foreground">Create or open a session to start.</p>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </SidebarProvider>
  )
}
