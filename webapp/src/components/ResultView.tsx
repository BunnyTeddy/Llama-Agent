import { useState } from 'react'

interface CheckResult {
    source_a: string
    source_b: string
    match: boolean
    note: string | null
}

interface ItemDetail {
    item_code: string
    item_name: string
    status: string
    checks: Record<string, CheckResult>
}

interface MatchSummary {
    status: string
    total_items: number
    matched: number
    mismatched: number
}

interface DocumentRefs {
    po_number: string
    dn_number: string
    inv_number: string
}

interface Report {
    match_summary: MatchSummary
    document_refs: DocumentRefs
    details: ItemDetail[]
    recommendation: string
}

interface ParsedItem {
    item_code?: string
    item_name?: string
    quantity?: number
    unit?: string
    unit_price?: number
    total?: number
}

interface ParsedDoc {
    po_number?: string
    dn_number?: string
    inv_number?: string
    date?: string
    supplier?: string
    items?: ParsedItem[]
    grand_total?: number
    subtotal?: number
    vat_rate?: number
    vat_amount?: number
    notes?: string
}

interface Props {
    report: Report
    summary: string
    parsedData?: { po: ParsedDoc; dn: ParsedDoc; inv: ParsedDoc }
}

/* ── Helper: extract numeric value from "PO (ordered): 100" style strings ── */
function extractValue(str: string): string {
    const parts = str.split(':')
    if (parts.length >= 2) return parts.slice(1).join(':').trim()
    return str
}

function formatCurrency(val: number | undefined): string {
    if (val === undefined || val === null) return '—'
    return new Intl.NumberFormat('vi-VN', {
        style: 'decimal',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(val)
}

/* ── Sub-components ──────────────────────────────────────────────────── */

function ScoreRing({ matched, total }: { matched: number; total: number }) {
    const pct = total > 0 ? Math.round((matched / total) * 100) : 0
    const circumference = 2 * Math.PI * 54
    const offset = circumference - (pct / 100) * circumference
    const isGood = pct === 100

    return (
        <div className="score-ring">
            <svg width="130" height="130" viewBox="0 0 130 130">
                <circle cx="65" cy="65" r="54" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
                <circle
                    cx="65" cy="65" r="54" fill="none"
                    stroke={isGood ? '#10b981' : '#ef4444'}
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    transform="rotate(-90 65 65)"
                    style={{ transition: 'stroke-dashoffset 1.2s ease' }}
                />
            </svg>
            <div className="score-ring__text">
                <span className="score-ring__pct">{pct}%</span>
                <span className="score-ring__label">Match</span>
            </div>
        </div>
    )
}

function StatCard({ icon, value, label, accent }: { icon: string; value: string | number; label: string; accent?: string }) {
    return (
        <div className={`rpt-stat ${accent ? `rpt-stat--${accent}` : ''}`}>
            <div className="rpt-stat__icon">{icon}</div>
            <div className="rpt-stat__value">{value}</div>
            <div className="rpt-stat__label">{label}</div>
        </div>
    )
}

function CheckRow({ label, check }: { label: string; check: CheckResult }) {
    const valA = extractValue(check.source_a)
    const valB = extractValue(check.source_b)
    const labelA = check.source_a.split(':')[0]?.trim() || 'Doc A'
    const labelB = check.source_b.split(':')[0]?.trim() || 'Doc B'

    return (
        <div className={`rpt-check-row ${check.match ? 'rpt-check-row--ok' : 'rpt-check-row--fail'}`}>
            <div className="rpt-check-row__indicator">
                {check.match ? (
                    <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="9" fill="#10b981" /><path d="M5.5 9.5L7.5 11.5L12.5 6.5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                ) : (
                    <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="9" fill="#ef4444" /><path d="M6.5 6.5L11.5 11.5M11.5 6.5L6.5 11.5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" /></svg>
                )}
            </div>
            <div className="rpt-check-row__label">{label}</div>
            <div className="rpt-check-row__values">
                <span className="rpt-check-row__tag">{labelA}</span>
                <span className="rpt-check-row__val">{valA}</span>
                <span className="rpt-check-row__arrow">→</span>
                <span className="rpt-check-row__tag">{labelB}</span>
                <span className="rpt-check-row__val">{valB}</span>
            </div>
            <div className={`rpt-check-row__badge ${check.match ? 'rpt-check-row__badge--ok' : 'rpt-check-row__badge--fail'}`}>
                {check.match ? 'Pass' : 'Fail'}
            </div>
            {!check.match && check.note && (
                <div className="rpt-check-row__note">⚠️ {check.note}</div>
            )}
        </div>
    )
}

/* ── Label Mapping ───────────────────────────────────────────────────── */
const CHECK_LABELS: Record<string, string> = {
    'quantity_po_vs_dn': 'Quantity: PO ↔ DN (Ordered vs Delivered)',
    'quantity_dn_vs_inv': 'Quantity: DN ↔ INV (Delivered vs Invoiced)',
    'unit_price_po_vs_inv': 'Unit Price: PO ↔ INV (Agreed vs Billed)',
    'line_total_verification': 'Line Total: Recalculated (Price × Qty) vs INV',
    'unexpected_item': 'Item Not Found in PO',
}

/* ── Main Component ──────────────────────────────────────────────────── */
export default function ResultView({ report, summary, parsedData }: Props) {
    const [expandedItems, setExpandedItems] = useState<Set<number>>(() => {
        // Auto-expand mismatched items
        const set = new Set<number>()
        report.details?.forEach((item, idx) => {
            if (item.status?.includes('🔴')) set.add(idx)
        })
        return set
    })
    const [activeTab, setActiveTab] = useState<'details' | 'data'>('details')

    const ms = report.match_summary || {} as MatchSummary
    const refs = report.document_refs || {} as DocumentRefs
    const details = report.details || []
    const isSuccess = ms.matched === ms.total_items && ms.total_items > 0

    const toggleItem = (idx: number) => {
        setExpandedItems(prev => {
            const next = new Set(prev)
            if (next.has(idx)) next.delete(idx)
            else next.add(idx)
            return next
        })
    }

    const expandAll = () => {
        setExpandedItems(new Set(details.map((_, i) => i)))
    }
    const collapseAll = () => {
        setExpandedItems(new Set())
    }

    return (
        <div className="rpt">
            {/* ── Executive Summary Banner ──────────────────────────── */}
            <div className={`rpt-banner ${isSuccess ? 'rpt-banner--success' : 'rpt-banner--fail'}`}>
                <div className="rpt-banner__content">
                    <div className="rpt-banner__left">
                        <div className="rpt-banner__status-icon">
                            {isSuccess ? '✅' : '⚠️'}
                        </div>
                        <div>
                            <h2 className="rpt-banner__title">
                                {isSuccess ? 'All Documents Matched' : 'Discrepancies Detected'}
                            </h2>
                            <p className="rpt-banner__subtitle">{report.recommendation}</p>
                        </div>
                    </div>
                    <ScoreRing matched={ms.matched || 0} total={ms.total_items || 0} />
                </div>

                {/* Stats row */}
                <div className="rpt-banner__stats">
                    <StatCard icon="📦" value={ms.total_items || 0} label="Total Items" />
                    <StatCard icon="✅" value={ms.matched || 0} label="Matched" accent="green" />
                    <StatCard icon="❌" value={ms.mismatched || 0} label="Mismatched" accent="red" />
                    <StatCard
                        icon="📄"
                        value={`${refs.po_number || '—'} / ${refs.inv_number || '—'}`}
                        label="PO / Invoice"
                    />
                </div>
            </div>

            {/* ── Document References ──────────────────────────────── */}
            <div className="rpt-docs">
                <div className="rpt-doc-card rpt-doc-card--po">
                    <div className="rpt-doc-card__icon">📋</div>
                    <div className="rpt-doc-card__info">
                        <span className="rpt-doc-card__type">Purchase Order</span>
                        <span className="rpt-doc-card__number">{refs.po_number}</span>
                        {parsedData?.po?.date && <span className="rpt-doc-card__date">📅 {parsedData.po.date}</span>}
                        {parsedData?.po?.supplier && <span className="rpt-doc-card__extra">🏢 {parsedData.po.supplier}</span>}
                    </div>
                    {parsedData?.po?.grand_total !== undefined && (
                        <div className="rpt-doc-card__total">{formatCurrency(parsedData.po.grand_total)}</div>
                    )}
                </div>
                <div className="rpt-doc-card rpt-doc-card--dn">
                    <div className="rpt-doc-card__icon">🚚</div>
                    <div className="rpt-doc-card__info">
                        <span className="rpt-doc-card__type">Delivery Note</span>
                        <span className="rpt-doc-card__number">{refs.dn_number}</span>
                        {parsedData?.dn?.date && <span className="rpt-doc-card__date">📅 {parsedData.dn.date}</span>}
                        {parsedData?.dn?.notes && <span className="rpt-doc-card__extra">📝 {parsedData.dn.notes}</span>}
                    </div>
                </div>
                <div className="rpt-doc-card rpt-doc-card--inv">
                    <div className="rpt-doc-card__icon">🧾</div>
                    <div className="rpt-doc-card__info">
                        <span className="rpt-doc-card__type">Invoice</span>
                        <span className="rpt-doc-card__number">{refs.inv_number}</span>
                        {parsedData?.inv?.date && <span className="rpt-doc-card__date">📅 {parsedData.inv.date}</span>}
                    </div>
                    {parsedData?.inv?.grand_total !== undefined && (
                        <div className="rpt-doc-card__total">
                            {formatCurrency(parsedData.inv.grand_total)}
                            {parsedData.inv.vat_rate !== undefined && (
                                <span className="rpt-doc-card__vat">VAT {parsedData.inv.vat_rate}%</span>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Tab Switcher ─────────────────────────────────────── */}
            <div className="rpt-tabs">
                <button
                    className={`rpt-tab ${activeTab === 'details' ? 'rpt-tab--active' : ''}`}
                    onClick={() => setActiveTab('details')}
                >
                    🔍 Match Details
                </button>
                <button
                    className={`rpt-tab ${activeTab === 'data' ? 'rpt-tab--active' : ''}`}
                    onClick={() => setActiveTab('data')}
                >
                    📊 Extracted Data
                </button>
            </div>

            {/* ── Details Tab ──────────────────────────────────────── */}
            {activeTab === 'details' && (
                <div className="rpt-details">
                    <div className="rpt-details__header">
                        <h3>📦 Item-by-Item Details ({details.length} items)</h3>
                        <div className="rpt-details__actions">
                            <button className="rpt-action-btn" onClick={expandAll}>Expand All</button>
                            <button className="rpt-action-btn" onClick={collapseAll}>Collapse All</button>
                        </div>
                    </div>

                    {details.map((item, idx) => {
                        const isMatch = item.status?.includes('Match') || item.status?.includes('🟢')
                        const isExpanded = expandedItems.has(idx)
                        const checkEntries = Object.entries(item.checks || {})
                        const passedChecks = checkEntries.filter(([, c]) => c.match).length

                        return (
                            <div className={`rpt-item ${isExpanded ? 'rpt-item--expanded' : ''} ${isMatch ? '' : 'rpt-item--fail'}`} key={idx}>
                                <div className="rpt-item__header" onClick={() => toggleItem(idx)}>
                                    <div className="rpt-item__left">
                                        <span className={`rpt-item__status-dot ${isMatch ? 'rpt-item__status-dot--ok' : 'rpt-item__status-dot--fail'}`} />
                                        <span className="rpt-item__code">{item.item_code}</span>
                                        <span className="rpt-item__name">{item.item_name}</span>
                                    </div>
                                    <div className="rpt-item__right">
                                        <span className="rpt-item__check-count">
                                            {passedChecks}/{checkEntries.length} checks passed
                                        </span>
                                        <span className={`rpt-item__badge ${isMatch ? 'rpt-item__badge--ok' : 'rpt-item__badge--fail'}`}>
                                            {isMatch ? '✓ Match' : '✗ Mismatch'}
                                        </span>
                                        <span className={`rpt-item__chevron ${isExpanded ? 'rpt-item__chevron--open' : ''}`}>
                                            ▾
                                        </span>
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="rpt-item__body">
                                        {/* Mini progress bar for this item */}
                                        <div className="rpt-item__progress">
                                            <div
                                                className="rpt-item__progress-fill"
                                                style={{
                                                    width: `${checkEntries.length > 0 ? (passedChecks / checkEntries.length) * 100 : 0}%`,
                                                    background: isMatch ? 'var(--green)' : 'var(--red)',
                                                }}
                                            />
                                        </div>
                                        {checkEntries.map(([key, check]) => (
                                            <CheckRow
                                                key={key}
                                                label={CHECK_LABELS[key] || key}
                                                check={check}
                                            />
                                        ))}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}

            {/* ── Data Tab ─────────────────────────────────────────── */}
            {activeTab === 'data' && parsedData && (
                <div className="rpt-data">
                    <DataTable title="Purchase Order" icon="📋" items={parsedData.po?.items} showPrice />
                    <DataTable title="Delivery Note" icon="🚚" items={parsedData.dn?.items} showPrice={false} />
                    <DataTable title="Invoice" icon="🧾" items={parsedData.inv?.items} showPrice />
                    {parsedData.inv?.subtotal !== undefined && (
                        <div className="rpt-data__totals">
                            <div className="rpt-data__total-row">
                                <span>Subtotal</span>
                                <span>{formatCurrency(parsedData.inv.subtotal)}</span>
                            </div>
                            {parsedData.inv.vat_amount !== undefined && (
                                <div className="rpt-data__total-row">
                                    <span>VAT ({parsedData.inv.vat_rate || 0}%)</span>
                                    <span>{formatCurrency(parsedData.inv.vat_amount)}</span>
                                </div>
                            )}
                            <div className="rpt-data__total-row rpt-data__total-row--grand">
                                <span>Grand Total</span>
                                <span>{formatCurrency(parsedData.inv.grand_total)}</span>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

/* ── Data Table sub-component ────────────────────────────────────────── */
function DataTable({ title, icon, items, showPrice }: { title: string; icon: string; items?: ParsedItem[]; showPrice: boolean }) {
    if (!items || items.length === 0) return null

    return (
        <div className="rpt-data__section">
            <h4>{icon} {title}</h4>
            <div className="rpt-data__table-wrap">
                <table className="rpt-table">
                    <thead>
                        <tr>
                            <th>Item Code</th>
                            <th>Item Name</th>
                            <th className="rpt-table--right">Quantity</th>
                            {showPrice && <th className="rpt-table--right">Unit Price</th>}
                            {showPrice && <th className="rpt-table--right">Total</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item, i) => (
                            <tr key={i}>
                                <td><code>{item.item_code}</code></td>
                                <td>{item.item_name}</td>
                                <td className="rpt-table--right">{item.quantity} {item.unit || ''}</td>
                                {showPrice && <td className="rpt-table--right">{formatCurrency(item.unit_price)}</td>}
                                {showPrice && <td className="rpt-table--right">{formatCurrency(item.total)}</td>}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
