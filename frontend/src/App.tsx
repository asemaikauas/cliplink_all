import Landing from './components/landing'
import Dashboard from './components/Dashboard'
import ClipsFolders from './components/ClipsFolders'
import FolderDetail from './components/FolderDetail'
import { SignedIn, UserButton, useAuth } from '@clerk/clerk-react'

export default function App() {
  const { isSignedIn, isLoaded } = useAuth();
  const path = window.location.pathname;

  // Show loading while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Protected routes - require authentication
  if (path === '/dashboard' || path === '/clips' || path.startsWith('/clips/')) {
    if (!isSignedIn) {
      // Redirect to landing page if not authenticated
      window.location.href = '/';
      return null;
    }

    // User is authenticated, show app with navigation
    return (
      <>
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center space-x-6">
                <h1 className="text-xl font-semibold text-gray-900">Cliplink AI</h1>
                <nav className="flex space-x-4">
                  <button
                    onClick={() => window.location.href = '/dashboard'}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${path === '/dashboard'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                      }`}
                  >
                    Home
                  </button>
                </nav>
              </div>
              <div className="flex items-center space-x-4">
                <SignedIn>
                  <UserButton afterSignOutUrl="/" />
                </SignedIn>
              </div>
            </div>
          </div>
        </header>
        {path === '/dashboard' && <Dashboard />}
        {path === '/clips' && <ClipsFolders />}
        {path.startsWith('/clips/') && <FolderDetail />}
      </>
    );
  }

  // Landing page - public access with embedded auth
  return <Landing />;
}
