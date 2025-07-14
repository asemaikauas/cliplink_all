// Frontend configuration
export const config = {
    // API Configuration
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

    // Clerk Configuration
    CLERK_PUBLISHABLE_KEY: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,

    // Environment
    NODE_ENV: import.meta.env.NODE_ENV || 'development',

    // API Endpoints (relative to API_BASE_URL)
    endpoints: {
        users: '/users',
        videos: '/videos',
        clips: '/clips',
        transcript: '/transcript',
        workflow: '/workflow',
        health: '/health'
    }
};

// Helper function to build full API URLs
export const apiUrl = (endpoint: string): string => {
    return `${config.API_BASE_URL}${endpoint}`;
};

// Helper function to build clip URLs
export const clipUrl = (clipPath: string): string => {
    const cleanPath = clipPath.replace(/\\/g, '/').split('/').pop();
    return `${config.API_BASE_URL}/clips/${cleanPath}`;
}; 