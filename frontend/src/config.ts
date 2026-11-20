// NetScope Frontend Configuration

/**
 * Environment-based configuration for the frontend application.
 * Uses VITE_API_URL environment variable for API endpoint.
 */

// Type declaration for import.meta.env
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Get API URL from environment variables with fallback
const getApiUrl = (): string => {
  const apiUrl = import.meta.env.VITE_API_URL;
  
  if (apiUrl) {
    return apiUrl;
  }
  
  // Default to nginx proxy port 3000 in development, backend port 8000 for direct access
  // In production builds, default to nginx proxy (port 3000) for CORS compatibility
  return "http://localhost:3000";
};

// Validate URL format
const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch (e) {
    return false;
  }
};

// Configuration object
const config = {
  // API Configuration
  apiUrl: getApiUrl(),
  
  // Validation
  validateConfig: (): boolean => {
    const url = config.apiUrl;
    if (!url) {
      console.error("API URL is not configured");
      return false;
    }
    
    if (!isValidUrl(url)) {
      console.error(`Invalid API URL: ${url}`);
      return false;
    }
    
    // In production, warn about localhost
    if (import.meta.env.PROD) {
      const urlObj = new URL(url);
      if (urlObj.hostname === "localhost" || urlObj.hostname === "127.0.0.1") {
        console.warn(
          "WARNING: Using localhost in production may cause connection issues. " +
          "Set VITE_API_URL to a proper server address."
        );
      }
    }
    
    return true;
  },
  
  // Security settings
  security: {
    // Enable HTTPS in production
    requireHttps: import.meta.env.PROD,
    
    // Token expiration (in minutes)
    tokenExpirationMinutes: 30,
    
    // Enable CSRF protection
    enableCsrf: true,
  },
  
  // Scan settings
  scan: {
    // Maximum concurrent scans
    maxConcurrentScans: 5,
    
    // Default scan timeout (in seconds)
    defaultTimeoutSeconds: 3600,
    
    // Maximum ports allowed in a single scan
    maxPortsPerScan: 1000,
    
    // Maximum scan targets per scan
    maxTargetsPerScan: 256,
  },
  
  // Logging settings
  logging: {
    // Log level: debug, info, warn, error
    level: import.meta.env.DEV ? "debug" : "info",
    
    // Enable detailed logging
    verbose: import.meta.env.DEV,
  },
};

// Export configuration for use throughout the application
export default config;

// Re-export for convenience
export { config };

// Helper function to get API endpoint URL
export const getApiEndpoint = (endpoint: string): string => {
  if (!config.validateConfig()) {
    throw new Error("Configuration validation failed");
  }
  
  // Ensure endpoint starts with a single slash
  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  
  // Remove trailing slash from apiUrl and join
  const cleanApiUrl = config.apiUrl.replace(/\/+$/, "");
  
  return `${cleanApiUrl}${normalizedEndpoint}`;
};

// Example usage:
// import { getApiEndpoint } from '@/config';
// const url = getApiEndpoint('/api/v1/scans');
