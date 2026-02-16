const STEPS = ['Upload PDFs', 'Parsing', 'Matching', 'Report']

interface Props {
    current: number  // 0=upload, 1=parsing, 2=matching, 3=report
}

export default function StepIndicator({ current }: Props) {
    return (
        <div className="steps">
            {STEPS.map((label, i) => {
                const isDone = i < current
                const isActive = i === current
                return (
                    <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
                        <div className={`step ${isActive ? 'step--active' : ''} ${isDone ? 'step--done' : ''}`}>
                            <div className="step__number">
                                {isDone ? '✓' : i + 1}
                            </div>
                            {label}
                        </div>
                        {i < STEPS.length - 1 && (
                            <div className={`step__line ${isDone ? 'step__line--done' : ''}`} />
                        )}
                    </div>
                )
            })}
        </div>
    )
}
