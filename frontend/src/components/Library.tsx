import { Trash2, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api, type LibraryDocument } from '@/lib/api'

interface Props {
  documents: LibraryDocument[]
  onChanged: () => void
}

const errorText = (e: unknown): string => (e instanceof Error ? e.message : 'failed')

export function Library({ documents, onChanged }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  async function upload(files: FileList | null) {
    if (!files) return
    await Promise.all(
      [...files].map((f) =>
        api.uploadDocument(f).catch((e: unknown) => toast.error(`${f.name}: ${errorText(e)}`)),
      ),
    )
    onChanged()
  }

  async function remove(d: LibraryDocument) {
    try {
      await api.deleteDocument(d.id)
    } catch (e) {
      toast.error(`${d.filename}: ${errorText(e)}`)
    }
    onChanged()
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          void upload(e.dataTransfer.files)
        }}
        className={`flex flex-col items-center gap-2 rounded-lg border border-dashed p-8 text-sm text-muted-foreground ${over ? 'bg-muted' : ''}`}
      >
        <Upload className="size-5" />
        Drop PDFs here or click to choose
      </button>
      <input
        ref={input}
        type="file"
        accept="application/pdf"
        multiple
        hidden
        onChange={(e) => {
          void upload(e.target.files)
          e.target.value = ''
        }}
      />
      {documents.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>File</TableHead>
              <TableHead>Pages</TableHead>
              <TableHead>Status</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((d) => (
              <TableRow key={d.id}>
                <TableCell className="max-w-64 truncate">{d.filename}</TableCell>
                <TableCell>{d.page_count ?? '—'}</TableCell>
                <TableCell>
                  <Badge
                    variant={d.status === 'failed' ? 'destructive' : d.status === 'ready' ? 'secondary' : 'outline'}
                    title={d.error ?? undefined}
                  >
                    {d.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Delete ${d.filename}`}
                    onClick={() => void remove(d)}
                  >
                    <Trash2 />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
