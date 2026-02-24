// Vercel Serverless Function — Proxy to LlamaIndex Cloud
// This avoids CORS issues by making server-to-server requests

export const config = {
    maxDuration: 300, // 5 minutes — PDF parsing can take a while
}

export default async function handler(req, res) {
    // Only allow POST
    if (req.method !== 'POST') {
        return res.status(405).json({ detail: 'Method not allowed' })
    }

    const LLAMA_API_URL = process.env.LLAMA_API_URL
    const LLAMA_API_KEY = process.env.LLAMA_API_KEY

    if (!LLAMA_API_URL || !LLAMA_API_KEY) {
        return res.status(500).json({
            detail: 'Server misconfigured: missing LLAMA_API_URL or LLAMA_API_KEY',
        })
    }

    try {
        const { po, dn, inv } = req.body

        if (!po || !dn || !inv) {
            return res.status(400).json({
                detail: 'Missing required fields: po, dn, inv (base64-encoded PDFs)',
            })
        }

        // Build the LlamaDeploy workflow request
        const workflowUrl = `${LLAMA_API_URL}/workflows/three_way_matcher/run`
        const inputPayload = JSON.stringify({ po, dn, inv })

        const response = await fetch(workflowUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${LLAMA_API_KEY}`,
            },
            body: JSON.stringify({ input: inputPayload }),
        })

        if (!response.ok) {
            const errorBody = await response.text()
            console.error('LlamaDeploy error:', response.status, errorBody)
            return res.status(response.status).json({
                detail: `Backend error: ${response.status} — ${errorBody}`,
            })
        }

        const rawData = await response.json()

        // Unwrap LlamaDeploy response envelope
        let result
        const resultStr = rawData.result || rawData
        if (typeof resultStr === 'string') {
            try {
                result = JSON.parse(resultStr)
            } catch {
                result = { report: null, summary: resultStr, parsed_data: null }
            }
        } else {
            result = resultStr
        }

        return res.status(200).json(result)

    } catch (error) {
        console.error('Proxy error:', error)
        return res.status(500).json({
            detail: `Proxy error: ${error.message}`,
        })
    }
}
