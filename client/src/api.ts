export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '')

// Rejections from the server carry a JSON `detail` (rate limit, size cap, ...). Show it instead of a bare status code.
export async function errorMessage(res: Response): Promise<string> {
    try {
        const body = await res.json()
        if (typeof body?.detail === 'string') return body.detail
    } catch { /* not JSON */ }
    // Our API never answers 403. An HTML 403 comes from the hosting provider's firewall, which rejects request
    // bodies containing attack signatures (a code reviewer is sent exactly that kind of text).
    if (res.status === 403) {
        return 'The hosting provider\'s firewall blocked this request, probably because the code contains an attack-like ' +
            'string (for example a path such as ../../etc/passwd). Remove or rephrase that part and try again.'
    }
    return `Server error ${res.status}`
}
