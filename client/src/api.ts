export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '')

// Rejections from the server carry a JSON `detail` (rate limit, size cap, ...). Show it instead of a bare status code.
export async function errorMessage(res: Response): Promise<string> {
    try {
        const body = await res.json()
        if (typeof body?.detail === 'string') return body.detail
    } catch { /* not JSON */ }
    return `Server error ${res.status}`
}
