import { useRef, useState, useCallback } from 'react'

interface Props {
    type: 'po' | 'dn' | 'inv'
    label: string
    sublabel: string
    icon: string
    file: File | null
    onFileChange: (type: 'po' | 'dn' | 'inv', file: File | null) => void
}

export default function FileUpload({ type, label, sublabel, icon, file, onFileChange }: Props) {
    const inputRef = useRef<HTMLInputElement>(null)
    const [dragover, setDragover] = useState(false)

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setDragover(false)
        const dropped = e.dataTransfer.files[0]
        if (dropped?.type === 'application/pdf') {
            onFileChange(type, dropped)
        }
    }, [type, onFileChange])

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setDragover(true)
    }, [])

    const handleDragLeave = useCallback(() => {
        setDragover(false)
    }, [])

    const handleClick = () => {
        inputRef.current?.click()
    }

    const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0]
        if (selected) onFileChange(type, selected)
    }

    const handleRemove = (e: React.MouseEvent) => {
        e.stopPropagation()
        onFileChange(type, null)
        if (inputRef.current) inputRef.current.value = ''
    }

    const cardClass = [
        'upload-card',
        dragover && 'upload-card--dragover',
        file && 'upload-card--filled',
    ].filter(Boolean).join(' ')

    return (
        <div
            className={cardClass}
            onClick={handleClick}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
        >
            <input
                ref={inputRef}
                type="file"
                accept=".pdf"
                onChange={handleInput}
                style={{ display: 'none' }}
            />

            <div className="upload-card__icon">{file ? '✅' : icon}</div>
            <div className="upload-card__label">{label}</div>
            <div className="upload-card__sublabel">{sublabel}</div>

            {file && (
                <>
                    <div className="upload-card__file">
                        📄 {file.name}
                    </div>
                    <button className="upload-card__remove" onClick={handleRemove}>✕</button>
                </>
            )}

            {!file && (
                <div className="upload-card__sublabel" style={{ marginTop: '0.5rem', fontSize: '0.65rem' }}>
                    Kéo thả hoặc click để chọn PDF
                </div>
            )}
        </div>
    )
}
