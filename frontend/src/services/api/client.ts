import axios from 'axios'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '')

/**
 * Centralized Axios HTTP client for FastAPI communication.
 * Note: Custom headers such as X-NEXORA-Workspace are intentionally NOT auto-injected yet
 * because Phase 1 backend routes do not consume workspace middleware headers today.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
})
