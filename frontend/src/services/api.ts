import {
  ForecastRequest,
  ForecastResponse,
  SupportedHorizonsResponse,
  HealthResponse
} from '../types/forecast'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

export class ApiError extends Error {
  status: number
  detail: any

  constructor(status: number, message: string, detail?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/**
 * Checks connectivity to the backend /health endpoint.
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/health`
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Accept': 'application/json' }
  })
  if (!response.ok) {
    throw new ApiError(response.status, `Backend health check failed with status ${response.status}`)
  }
  return response.json()
}

/**
 * Fetches the supported forecasting horizons from /api/v1/forecast/horizons.
 */
export async function fetchSupportedHorizons(): Promise<SupportedHorizonsResponse> {
  const url = `${API_BASE_URL}/api/v1/forecast/horizons`
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Accept': 'application/json' }
  })
  if (!response.ok) {
    throw new ApiError(response.status, `Failed to load horizons metadata with status ${response.status}`)
  }
  return response.json()
}

/**
 * Submits a multi-horizon demand forecast request to POST /api/v1/forecast/.
 */
export async function submitForecast(payload: ForecastRequest): Promise<ForecastResponse> {
  const url = `${API_BASE_URL}/api/v1/forecast/`
  
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload)
    })
  } catch (err: any) {
    throw new ApiError(
      0,
      `Cannot connect to FastAPI backend at ${API_BASE_URL}. Is the server running? (${err.message})`
    )
  }

  const responseText = await response.text()
  let responseData: any
  try {
    responseData = JSON.parse(responseText)
  } catch {
    responseData = { detail: responseText }
  }

  if (!response.ok) {
    let errorMessage = `API request failed with HTTP ${response.status}`
    if (responseData.detail) {
      if (typeof responseData.detail === 'string') {
        errorMessage = responseData.detail
      } else if (Array.isArray(responseData.detail)) {
        // Pydantic validation errors list
        errorMessage = responseData.detail
          .map((d: any) => `${d.loc ? d.loc.join('.') : 'Field'}: ${d.msg}`)
          .join('; ')
      }
    }
    throw new ApiError(response.status, errorMessage, responseData)
  }

  return responseData as ForecastResponse
}
