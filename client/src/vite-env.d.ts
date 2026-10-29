/// <reference types="vite/client" />

interface ImportMetaEnv {
    // Set at build time when the API lives on a different origin than the page. Empty means same origin.
    readonly VITE_API_BASE?: string
}
