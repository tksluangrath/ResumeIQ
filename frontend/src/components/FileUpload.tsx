import { useRef, useState } from 'react'
import { Upload, FileText, X } from 'lucide-react'

interface Props {
  file: File | null
  onChange: (file: File | null) => void
}

export default function FileUpload({ file, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped?.type === 'application/pdf') onChange(dropped)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current?.click()}
      className={`relative rounded-xl border-2 border-dashed transition-colors cursor-pointer ${
        dragging ? 'border-brand bg-brand/5' : 'border-slate-300 hover:border-brand/60 bg-slate-50'
      } ${file ? 'cursor-default' : ''}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />

      {file ? (
        <div className="flex items-center gap-3 p-4">
          <FileText className="text-brand shrink-0" size={24} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">{file.name}</p>
            <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB</p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onChange(null) }}
            className="text-slate-400 hover:text-slate-700 transition-colors"
          >
            <X size={18} />
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 py-8 px-4 text-center">
          <Upload className="text-slate-400" size={28} />
          <p className="text-sm text-slate-600 font-medium">Drop your resume PDF here</p>
          <p className="text-xs text-slate-400">or click to browse · max 5MB</p>
        </div>
      )}
    </div>
  )
}
