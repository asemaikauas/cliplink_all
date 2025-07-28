import { useEffect, useState } from 'react';
import Landing from './components/landing'
import Dashboard from './components/Dashboard'
import TermsOfService from './components/TermsOfService'
import PrivacyPolicy from './components/PrivacyPolicy'
import { SignedIn, UserButton, useAuth } from '@clerk/clerk-react'
import VideoProcessor from './components/VideoProcessor'
import { t } from './lib/i18n'
import LanguageSelector from './components/shared/LanguageSelector'
import LanguageWelcomeModal, { useLanguageWelcome } from './components/shared/LanguageWelcomeModal'

export default function App() {
  const { isSignedIn, isLoaded } = useAuth();
  const path = window.location.pathname;
  const [, forceUpdate] = useState({});
  const { showModal, closeModal } = useLanguageWelcome();

  // Listen for language changes to re-render
  useEffect(() => {
    const handleLanguageChange = () => {
      forceUpdate({});
    };

    window.addEventListener('languageChanged', handleLanguageChange);
    return () => window.removeEventListener('languageChanged', handleLanguageChange);
  }, []);

  // Show loading while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">{t('loading')}</p>
        </div>
      </div>
    );
  }

  // Terms of Service page - public access
  if (path === '/terms') {
    return <TermsOfService />;
  }

  // Privacy Policy page - public access
  if (path === '/privacy') {
    return <PrivacyPolicy />;
  }

  // Protected routes - require authentication
  if (path === '/dashboard' || path === '/process') {
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
                <h1 className="text-xl font-semibold text-gray-900">{t('appTagline')}</h1>
                <nav className="flex space-x-4">
                  <button
                    onClick={() => window.location.href = '/dashboard'}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${path === '/dashboard'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                      }`}
                  >
                    {t('navDashboard')}
                  </button>
                </nav>
              </div>
              <div className="flex items-center space-x-4">
                <LanguageSelector variant="default" />
                <SignedIn>
                  <UserButton afterSignOutUrl="/" />
                </SignedIn>
              </div>
            </div>
          </div>
        </header>
        {path === '/dashboard' && <Dashboard />}
        {path === '/process' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">🎬 {t('processorTitle')}</h1>
              <p className="text-gray-600">{t('processorSubtitle')}</p>
            </div>
            <VideoProcessor />
          </div>
        )}

        {/* Language Welcome Modal */}
        {showModal && <LanguageWelcomeModal onClose={closeModal} />}
      </>
    );
  }

  // Landing page - public access with embedded auth
  return (
    <>
      <Landing />
      {/* Language Welcome Modal */}
      {showModal && <LanguageWelcomeModal onClose={closeModal} />}
    </>
  );
}
