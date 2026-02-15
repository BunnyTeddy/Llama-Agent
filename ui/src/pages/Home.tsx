import { useState } from "react";
import { useWorkflow, useWorkflowRun } from "@llamaindex/ui";

export default function Home() {
    const [input, setInput] = useState("");
    const [result, setResult] = useState<string | null>(null);
    const { runWorkflow } = useWorkflow("three_way_matcher");

    const handleRun = async () => {
        if (!input.trim()) return;
        setResult(null);
        const handler = await runWorkflow(input);
        if (handler) {
            const res = await handler;
            setResult(typeof res === "string" ? res : JSON.stringify(res, null, 2));
        }
    };

    return (
        <div
            style={{
                maxWidth: 800,
                margin: "0 auto",
                padding: "2rem",
                fontFamily: "system-ui, sans-serif",
            }}
        >
            <h1 style={{ fontSize: "1.8rem", marginBottom: "0.5rem" }}>
                🔄 3-Way Matcher
            </h1>
            <p style={{ color: "#666", marginBottom: "1.5rem" }}>
                Supply Chain Document Reconciliation Agent
            </p>

            <div style={{ marginBottom: "1rem" }}>
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Enter file paths for matching, e.g.:\nPO: /path/to/purchase_order.pdf\nDN: /path/to/delivery_note.pdf\nINV: /path/to/invoice.pdf`}
                    style={{
                        width: "100%",
                        minHeight: 120,
                        padding: "0.75rem",
                        border: "1px solid #ddd",
                        borderRadius: 8,
                        fontSize: "0.9rem",
                        fontFamily: "monospace",
                        resize: "vertical",
                    }}
                />
            </div>

            <button
                onClick={handleRun}
                style={{
                    padding: "0.6rem 1.5rem",
                    background: "#7c3aed",
                    color: "white",
                    border: "none",
                    borderRadius: 8,
                    cursor: "pointer",
                    fontSize: "1rem",
                    fontWeight: 600,
                }}
            >
                ▶ Run 3-Way Match
            </button>

            {result && (
                <pre
                    style={{
                        marginTop: "1.5rem",
                        padding: "1rem",
                        background: "#f5f5f5",
                        borderRadius: 8,
                        overflow: "auto",
                        fontSize: "0.85rem",
                        whiteSpace: "pre-wrap",
                    }}
                >
                    {result}
                </pre>
            )}
        </div>
    );
}
