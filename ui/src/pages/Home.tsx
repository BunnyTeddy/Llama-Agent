import { useState } from "react";

interface HomeProps {
    deploymentName: string;
    basePath: string;
}

export default function Home({ deploymentName, basePath }: HomeProps) {
    const [input, setInput] = useState("");
    const [result, setResult] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleRun = async () => {
        if (!input.trim()) return;
        setLoading(true);
        setResult(null);

        try {
            const apiBase = basePath || `/deployments/${deploymentName}`;
            const response = await fetch(`${apiBase}/workflows/three_way_matcher`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ input: input }),
            });
            const data = await response.json();
            setResult(
                typeof data === "string" ? data : JSON.stringify(data, null, 2)
            );
        } catch (err: unknown) {
            setResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
        } finally {
            setLoading(false);
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
            <p style={{ color: "#888", marginBottom: "1.5rem" }}>
                Supply Chain Document Reconciliation Agent
            </p>

            <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={`Paste PO, DN, and Invoice JSON data here. Example:\n{\n  "po": { "po_number": "PO-001", "items": [...] },\n  "dn": { "dn_number": "DN-001", "items": [...] },\n  "inv": { "inv_number": "INV-001", "items": [...] }\n}`}
                style={{
                    width: "100%",
                    minHeight: 150,
                    padding: "0.75rem",
                    border: "1px solid #333",
                    borderRadius: 8,
                    fontSize: "0.9rem",
                    fontFamily: "monospace",
                    resize: "vertical",
                    background: "#1a1a1a",
                    color: "#eee",
                }}
            />

            <button
                onClick={handleRun}
                disabled={loading}
                style={{
                    marginTop: "0.75rem",
                    padding: "0.6rem 1.5rem",
                    background: loading ? "#555" : "#7c3aed",
                    color: "white",
                    border: "none",
                    borderRadius: 8,
                    cursor: loading ? "wait" : "pointer",
                    fontSize: "1rem",
                    fontWeight: 600,
                }}
            >
                {loading ? "⏳ Processing..." : "▶ Run 3-Way Match"}
            </button>

            {result && (
                <pre
                    style={{
                        marginTop: "1.5rem",
                        padding: "1rem",
                        background: "#111",
                        color: "#0f0",
                        borderRadius: 8,
                        overflow: "auto",
                        fontSize: "0.85rem",
                        whiteSpace: "pre-wrap",
                        border: "1px solid #333",
                    }}
                >
                    {result}
                </pre>
            )}
        </div>
    );
}
