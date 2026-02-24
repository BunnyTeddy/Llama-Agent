import { useState, useCallback } from 'react'
import FileUpload from './components/FileUpload'
import StepIndicator from './components/StepIndicator'
import ResultView from './components/ResultView'

// LlamaDeploy API config
const API_URL = import.meta.env.VITE_API_URL || ''
const API_KEY = import.meta.env.VITE_LLAMA_API_KEY || ''

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

/** Convert a File to base64 string (without data URI prefix) */
function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => {
            const result = reader.result as string
            // Remove "data:application/pdf;base64," prefix
            const base64 = result.split(',')[1]
            resolve(base64)
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
    })
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
        setProgress({ percent: 10, label: '📤 Converting PDFs...', status: 'Preparing files...' })

        try {
            // Convert PDFs to base64
            setProgress({ percent: 20, label: '📤 Encoding PDFs to base64...', status: 'Encoding files...' })
            const [poB64, dnB64, invB64] = await Promise.all([
                fileToBase64(files.po),
                fileToBase64(files.dn),
                fileToBase64(files.inv),
            ])

            setProgress({ percent: 30, label: '🚀 Sending to AI backend...', status: 'Calling LlamaIndex Cloud...' })

            // Simulate progress while waiting for the API
            const progressTimer = setInterval(() => {
                setProgress(prev => {
                    if (prev.percent >= 90) {
                        clearInterval(progressTimer)
                        return prev
                    }
                    const newPercent = prev.percent + 5
                    const stages = [
                        { at: 35, label: '📝 Parsing Purchase Order...', status: 'LlamaParse extracting PO data...' },
                        { at: 50, label: '📝 Parsing Delivery Note...', status: 'LlamaParse extracting DN data...' },
                        { at: 65, label: '📝 Parsing Invoice...', status: 'LlamaParse extracting Invoice data...' },
                        { at: 80, label: '🔀 Cross-referencing...', status: 'AI matching 3 documents...' },
                        { at: 90, label: '📊 Generating report...', status: 'Finalizing match report...' },
                    ]
                    const stage = stages.filter(s => newPercent >= s.at).pop()
                    return { percent: newPercent, label: stage?.label || prev.label, status: stage?.status || prev.status }
                })
            }, 3000)

            // Build the LlamaDeploy API request
            const inputPayload = JSON.stringify({
                po: poB64,
                dn: dnB64,
                inv: invB64,
            })

            // Determine endpoint — if API_URL includes /deployments/, use workflow path directly
            // Otherwise, assume it's the base deployment URL
            const workflowUrl = API_URL.includes('/deployments/')
                ? `${API_URL}/workflows/three_way_matcher/run`
                : `${API_URL}/deployments/three-way-matcher/workflows/three_way_matcher/run`

            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            }
            if (API_KEY) {
                headers['Authorization'] = `Bearer ${API_KEY}`
            }

            const response = await fetch(workflowUrl, {
                method: 'POST',
                headers,
                body: JSON.stringify({ input: inputPayload }),
            })

            clearInterval(progressTimer)

            if (!response.ok) {
                const err = await response.json().catch(() => ({ detail: response.statusText }))
                throw new Error(err.detail || `Server error: ${response.status}`)
            }

            const rawData = await response.json()

            // LlamaDeploy wraps the result — extract it
            // The result could be in rawData.result or rawData directly
            let data: MatchResult
            const resultStr = rawData.result || rawData
            if (typeof resultStr === 'string') {
                data = JSON.parse(resultStr)
            } else {
                data = resultStr
            }

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
