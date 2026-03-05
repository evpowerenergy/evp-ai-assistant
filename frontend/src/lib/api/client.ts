/**
 * Backend API Client
 */
import axios, { AxiosError } from 'axios'

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    // Token will be added per request from hooks
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const errorDetail = error.response?.data?.detail || 'Unauthorized'
      console.error('Authentication failed:', errorDetail)
      
      // Log the error for debugging
      console.log('401 Error Details:', {
        url: error.config?.url,
        method: error.config?.method,
        hasAuthHeader: !!error.config?.headers?.Authorization,
      })

      // Only redirect if we're not already on login page and not in a retry
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        // Show error message first
        const errorMessage = typeof errorDetail === 'string' ? errorDetail : 'Session expired. Please login again.'
        
        // Delay redirect to allow error to be displayed
        setTimeout(() => {
          // Clear any stored session data
          if (typeof localStorage !== 'undefined') {
            localStorage.removeItem('supabase.auth.token')
          }
          window.location.href = '/login'
        }, 2000) // Increased delay to 2 seconds
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
