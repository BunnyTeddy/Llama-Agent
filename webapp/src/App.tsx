import { useState, useCallback } from 'react'
import FileUpload from './components/FileUpload'
import StepIndicator from './components/StepIndicator'
import ResultView from './components/ResultView'

// In dev: empty string → uses Vite proxy (/api/match)
// In production: set VITE_API_URL to your backend URL (e.g. https://your-app.llamaindex.ai)
const API_BASE = import.meta.env.VITE_API_URL || ''

type AppState = 'upload' | 'processing' | 'done' | 'error'

interface MatchResult {
    report: any
    summary: string
    parsed_data: { po: any; dn: any; inv: any }
}

interface ProcessingProgress {
    percent: number
    label: string
    status: string
}

export default function App() {
    const [files, setFiles] = useState<{ po: File | null; dn: File | null; inv: File | null }>({
        po: null, dn: null, inv: null,
    })
    const [appState, setAppState] = useState<AppState>('upload')
    const [progress, setProgress] = useState<ProcessingProgress>({ percent: 0, label: '', status: '' })
    const [result, setResult] = useState<MatchResult | null>(null)
    const [error, setError] = useState<string>('')

    const allUploaded = files.po && files.dn && files.inv

    const currentStep = appState === 'upload' ? 0
        : appState === 'processing' ? 1
            : appState === 'done' ? 3
                : 0

    const handleFileChange = useCallback((type: 'po' | 'dn' | 'inv', file: File | null) => {
        setFiles(prev => ({ ...prev, [type]: file }))
    }, [])

    const handleRun = async () => {
        if (!files.po || !files.dn || !files.inv) return

        setAppState('processing')
        setError('')
        setProgress({ percent: 10, label: '📤 Uploading PDFs...', status: 'Uploading files...' })

        try {
            const formData = new FormData()
            formData.append('po', files.po)
            formData.append('dn', files.dn)
            formData.append('inv', files.inv)

            // Simulate progress stages
            setProgress({ percent: 25, label: '📝 Parsing with LlamaParse...', status: 'Reading PDFs with LlamaParse...' })

            const progressTimer = setInterval(() => {
                setProgress(prev => {
                    if (prev.percent >= 85) {
                        clearInterval(progressTimer)
                        return prev
                    }
                    const newPercent = prev.percent + 5
                    const stages = [
                        { at: 30, label: '📝 Parsing Purchase Order...', status: 'Extracting PO data...' },
                        { at: 45, label: '📝 Parsing Delivery Note...', status: 'Extracting DN data...' },
                        { at: 60, label: '📝 Parsing Invoice...', status: 'Extracting Invoice data...' },
                        { at: 75, label: '🔀 Cross-referencing...', status: 'Cross-referencing 3 documents...' },
                        { at: 85, label: '📊 Generating report...', status: 'Generating match report...' },
                    ]
                    const stage = stages.filter(s => newPercent >= s.at).pop()
                    return { percent: newPercent, label: stage?.label || prev.label, status: stage?.status || prev.status }
                })
            }, 2000)

            const response = await fetch(`${API_BASE}/api/match`, {
                method: 'POST',
                body: formData,
            })

            clearInterval(progressTimer)

            if (!response.ok) {
                const err = await response.json().catch(() => ({ detail: response.statusText }))
                throw new Error(err.detail || `Server error: ${response.status}`)
            }

            const data = await response.json()
            setProgress({ percent: 100, label: '✅ Done!', status: 'Complete!' })

            setTimeout(() => {
                setResult(data)
                setAppState('done')
            }, 500)

        } catch (err: any) {
            setError(err.message || 'Something went wrong')
            setAppState('error')
        }
    }

    const handleReset = () => {
        setFiles({ po: null, dn: null, inv: null })
        setAppState('upload')
        setResult(null)
        setError('')
        setProgress({ percent: 0, label: '', status: '' })
    }

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="header__badge">
                    <span></span> AI-Powered Supply Chain
                </div>
                <h1>3-Way Matcher</h1>
                <p>Upload Purchase Order, Delivery Note, and Invoice for automated AI reconciliation</p>
            </header>

            {/* Step Indicator */}
            <StepIndicator current={currentStep} />

            {/* Upload Area */}
            {(appState === 'upload' || appState === 'error') && (
                <>
                    <div className="upload-grid">
                        <FileUpload
                            type="po"
                            label="Purchase Order"
                            sublabel="PO Document"
                            icon="📋"
                            file={files.po}
                            onFileChange={handleFileChange}
                        />
                        <FileUpload
                            type="dn"
                            label="Delivery Note"
                            sublabel="DN Document"
                            icon="🚚"
                            file={files.dn}
                            onFileChange={handleFileChange}
                        />
                        <FileUpload
                            type="inv"
                            label="Invoice"
                            sublabel="INV Document"
                            icon="🧾"
                            file={files.inv}
                            onFileChange={handleFileChange}
                        />
                    </div>

                    {error && (
                        <div className="error-card">
                            <h3>❌ Processing Error</h3>
                            <p>{error}</p>
                        </div>
                    )}

                    <div className="run-section">
                        <button
                            className="run-btn"
                            disabled={!allUploaded}
                            onClick={handleRun}
                        >
                            🚀 Start Matching
                        </button>
                    </div>
                </>
            )}

            {/* Processing */}
            {appState === 'processing' && (
                <div className="progress">
                    <div className="progress__label">{progress.label}</div>
                    <div className="progress__bar">
                        <div className="progress__fill" style={{ width: `${progress.percent}%` }} />
                    </div>
                    <div className="progress__status">{progress.status}</div>
                </div>
            )}

            {/* Results */}
            {appState === 'done' && result && (
                <div className="result">
                    <ResultView report={result.report} summary={result.summary} parsedData={result.parsed_data} />
                    <div style={{ textAlign: 'center' }}>
                        <button className="reset-btn" onClick={handleReset}>
                            🔄 Match Another Set
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
