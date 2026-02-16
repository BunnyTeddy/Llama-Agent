import { useState } from 'react'

interface Props {
    report: {
        po_number?: string
        dn_number?: string
        inv_number?: string
        overall_status?: string
        recommendation?: string
        items?: any[]
    }
    summary: string
}

export default function ResultView({ report, summary }: Props) {
    const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set([0]))

    const isSuccess = report.overall_status?.includes('KHỚP') || report.overall_status?.includes('✅')

    const toggleItem = (idx: number) => {
        setExpandedItems(prev => {
            const next = new Set(prev)
            if (next.has(idx)) next.delete(idx)
            else next.add(idx)
            return next
        })
    }

    const formatCheckLabel = (key: string) => {
        const map: Record<string, string> = {
            'quantity_po_vs_dn': 'SL: PO ↔ DN',
            'quantity_dn_vs_inv': 'SL: DN ↔ INV',
            'unit_price_po_vs_inv': 'Đơn giá: PO ↔ INV',
        }
        return map[key] || key
    }

    return (
        <>
            {/* Banner */}
            <div className={`result__banner ${isSuccess ? 'result__banner--success' : 'result__banner--fail'}`}>
                <h2>{report.overall_status}</h2>
                <p>{report.recommendation}</p>
            </div>

            {/* Document Numbers */}
            <div className="doc-numbers">
                <div className="doc-num">
                    <div className="doc-num__label">Purchase Order</div>
                    <div className="doc-num__value">{report.po_number || 'N/A'}</div>
                </div>
                <div className="doc-num">
                    <div className="doc-num__label">Delivery Note</div>
                    <div className="doc-num__value">{report.dn_number || 'N/A'}</div>
                </div>
                <div className="doc-num">
                    <div className="doc-num__label">Invoice</div>
                    <div className="doc-num__value">{report.inv_number || 'N/A'}</div>
                </div>
            </div>

            {/* Items */}
            <div className="items-section">
                <h3>📦 Chi tiết từng mặt hàng ({report.items?.length || 0} items)</h3>

                {report.items?.map((item, idx) => {
                    const isMatch = item.status?.includes('KHỚP')
                    const isExpanded = expandedItems.has(idx)

                    return (
                        <div className="item-card" key={idx}>
                            <div className="item-card__header" onClick={() => toggleItem(idx)}>
                                <div className="item-card__name">
                                    <span className="item-card__code">{item.item_code}</span>
                                    <span className="item-card__title">{item.item_name}</span>
                                </div>
                                <span className={`status-badge ${isMatch ? 'status-badge--match' : 'status-badge--mismatch'}`}>
                                    {item.status}
                                </span>
                            </div>

                            {isExpanded && item.checks && (
                                <div className="item-card__checks">
                                    {Object.entries(item.checks).map(([key, check]: [string, any]) => (
                                        <div className="check" key={key}>
                                            <div className="check__label">{formatCheckLabel(key)}</div>
                                            <div className={`check__values ${check.match ? 'check__values--match' : 'check__values--mismatch'}`}>
                                                <span>{check.status}</span>
                                                {!check.match && Object.entries(check)
                                                    .filter(([k]) => !['match', 'status'].includes(k))
                                                    .map(([k, v]) => (
                                                        <span key={k} style={{ fontSize: '0.7rem', opacity: 0.8 }}>
                                                            {k}: {String(v)}
                                                        </span>
                                                    ))
                                                }
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </>
    )
}
