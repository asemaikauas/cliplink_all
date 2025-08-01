import { useState, useEffect } from 'react';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import { apiUrl } from '../config';
import { t } from '../lib/i18n';
import LanguageSelector from './shared/LanguageSelector';

const features = [
    {
        icon: (
            <span className="w-16 h-16 flex items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-purple-700">
                <svg className="w-10 h-10" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
            </span>
        ),
        titleKey: 'featureAITitle',
        descKey: 'featureAIDesc'
    },
    {
        icon: (
            <span className="w-16 h-16 flex items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-purple-700">
                <svg className="w-10 h-10" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="4" /><path strokeLinecap="round" strokeLinejoin="round" d="M8 8h8v8H8z" /></svg>
            </span>
        ),
        titleKey: 'featureEasyTitle',
        descKey: 'featureEasyDesc'
    },
    {
        icon: (
            <span className="w-16 h-16 flex items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-purple-700">
                <svg className="w-10 h-10" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3" /><circle cx="12" cy="12" r="10" /></svg>
            </span>
        ),
        titleKey: 'featureFastTitle',
        descKey: 'featureFastDesc'
    },
];

// Function to save URL to localStorage
const saveUrlForLater = (url: string) => {
    if (url.trim()) {
        localStorage.setItem('pendingYouTubeUrl', url.trim());
        console.log('💾 Saved URL for after authentication:', url.trim());
    }
};

// Function to get saved URL
export const getPendingUrl = (): string | null => {
    return localStorage.getItem('pendingYouTubeUrl');
};

// Function to clear saved URL
export const clearPendingUrl = () => {
    localStorage.removeItem('pendingYouTubeUrl');
};

export default function EtailLanding() {
    const [inputValue, setInputValue] = useState('');
    const [transcript, setTranscript] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [, forceUpdate] = useState({});

    // Listen for language changes to re-render
    useEffect(() => {
        const handleLanguageChange = () => {
            forceUpdate({});
        };

        window.addEventListener('languageChanged', handleLanguageChange);
        return () => window.removeEventListener('languageChanged', handleLanguageChange);
    }, []);

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const handleGetClips = async () => {
        setLoading(true);
        setTranscript('');
        setError('');
        try {
            const response = await fetch(apiUrl('/api/transcript'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ youtube_url: inputValue }),
            });
            if (!response.ok) {
                throw new Error('Failed to fetch transcript');
            }
            const data = await response.json();
            setTranscript(data.transcript);
        } catch (err) {
            setError('Error fetching transcript.');
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex flex-col bg-black relative overflow-x-hidden font-sans">
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute -top-32 -left-32 w-[600px] h-[600px] bg-gradient-to-br from-purple-700 via-purple-900 to-black opacity-40 rounded-full blur-3xl" />
                <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-gradient-to-tr from-purple-600 to-black opacity-30 rounded-full blur-2xl" />
            </div>

            <header className="sticky top-0 w-full z-20 bg-black/60 backdrop-blur-md flex justify-between items-center px-4 sm:px-8 py-4 border-b border-purple-900">
                <div className="text-xl sm:text-2xl font-extrabold text-purple-400 tracking-tight">{t('appName')}</div>
                <div className="flex items-center gap-2 sm:gap-4">
                    <LanguageSelector variant="compact" />
                    <SignedOut>
                        <SignInButton mode="modal" fallbackRedirectUrl="/dashboard">
                            <button className="bg-gradient-to-r from-purple-600 to-purple-400 text-white px-4 sm:px-6 py-2 rounded-full font-semibold shadow-lg hover:scale-105 transition-all text-sm sm:text-base flex-shrink-0">
                                {t('navSignIn')}
                            </button>
                        </SignInButton>
                    </SignedOut>
                    <SignedIn>
                        <button
                            onClick={() => window.location.href = '/dashboard'}
                            className="bg-green-600 hover:bg-green-700 text-white px-3 sm:px-4 py-2 rounded-full font-semibold shadow-lg hover:scale-105 transition-all text-sm sm:text-base flex-shrink-0"
                        >
                            {t('navDashboard')}
                        </button>
                        <div className="flex-shrink-0">
                            <UserButton afterSignOutUrl="/" />
                        </div>
                    </SignedIn>
                </div>
            </header>

            <section className="flex flex-col items-center justify-center flex-1 py-20 z-10">
                <h1 className="text-4xl sm:text-5xl md:text-7xl font-extrabold text-center bg-gradient-to-r from-purple-400 via-white to-purple-600 bg-clip-text text-transparent drop-shadow-lg mb-6 px-4">
                    {t('landingHeadline')}
                </h1>
                <p className="text-lg sm:text-xl md:text-2xl text-gray-300 text-center mb-12 max-w-2xl px-4">
                    {t('landingSubtitle')}
                </p>
                <div className="w-full flex flex-col items-center mt-6 px-4 space-y-4">
                    {/* Input Container */}
                    <div
                        className="w-full max-w-xl bg-[#19181d]/90 border-4 border-purple-700 rounded-full shadow-2xl backdrop-blur-md"
                        style={{
                            boxShadow: '0 0 16px 0 #a855f7, 0 2px 8px 0 #0008',
                        }}
                    >
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder={t('landingInputPlaceholder')}
                            className="w-full bg-transparent outline-none text-gray-200 text-lg sm:text-xl placeholder-gray-500 px-6 py-4 rounded-full border-0"
                        />
                    </div>

                    {/* Button Container */}
                    <div className="w-full flex justify-center">
                        <SignedOut>
                            <SignInButton mode="modal" fallbackRedirectUrl="/dashboard">
                                <button
                                    onClick={() => saveUrlForLater(inputValue)}
                                    className="px-8 py-4 text-white font-bold text-lg sm:text-xl rounded-full bg-purple-500 hover:bg-purple-600 transition-all whitespace-nowrap shadow-lg"
                                >
                                    {t('landingCTA')}
                                </button>
                            </SignInButton>
                        </SignedOut>
                        <SignedIn>
                            <button
                                onClick={() => {
                                    if (inputValue.trim()) {
                                        saveUrlForLater(inputValue);
                                        window.location.href = '/dashboard';
                                    } else {
                                        alert(t('errorYouTubeUrl'));
                                    }
                                }}
                                className="px-8 py-4 text-white font-bold text-lg sm:text-xl rounded-full bg-purple-500 hover:bg-purple-600 transition-all whitespace-nowrap shadow-lg"
                            >
                                {t('landingCTA')}
                            </button>
                        </SignedIn>
                    </div>

                    <span className="text-gray-400 text-sm sm:text-base text-center">{t('landingSubCTA')}</span>
                </div>
                {error && <div className="text-red-500 mt-4">{error}</div>}
                {transcript && (
                    <div className="mt-8 max-w-2xl mx-auto bg-[#18181a] p-6 rounded-xl border border-purple-700 text-gray-200" style={{ whiteSpace: 'pre-wrap' }}>
                        <h3 className="text-lg font-bold mb-2 text-purple-300">Transcript:</h3>
                        {transcript}
                    </div>
                )}
            </section>

            <section className="w-full flex justify-center items-center py-16 z-10">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-10 w-full max-w-6xl px-4">
                    {features.map((f, i) => (
                        <div key={i} className="bg-[#18181a] rounded-2xl border-2 border-purple-500 p-10 flex flex-col items-center text-center shadow-lg transition-all">
                            <div className="mb-6 flex items-center justify-center">
                                {f.icon}
                            </div>
                            <h3 className="text-2xl font-extrabold text-purple-200 mb-3">{t(f.titleKey as keyof typeof import('../lib/i18n').translations)}</h3>
                            <p className="text-gray-400 text-lg">{t(f.descKey as keyof typeof import('../lib/i18n').translations)}</p>
                        </div>
                    ))}
                </div>
            </section>

            <section id="get-started" className="w-full flex flex-col items-center py-20 bg-gradient-to-t from-black via-[#18181a] to-black z-10">
                <h2 className="text-3xl md:text-4xl font-extrabold text-center text-purple-200 mb-6">{t('startForFree')}</h2>
                <p className="text-lg text-gray-300 mb-8 text-center">{t('noCreditCard')}</p>
                <SignedOut>
                    <SignInButton mode="modal" fallbackRedirectUrl="/dashboard">
                        <button
                            onClick={() => saveUrlForLater(inputValue)}
                            className="bg-gradient-to-r from-purple-500 to-purple-700 text-white font-bold text-xl px-12 py-5 rounded-full shadow-xl hover:scale-105 transition-all"
                        >
                            {t('landingTryNow')}
                        </button>
                    </SignInButton>
                </SignedOut>
                <SignedIn>
                    <button
                        onClick={() => window.location.href = '/dashboard'}
                        className="bg-gradient-to-r from-purple-500 to-purple-700 text-white font-bold text-xl px-12 py-5 rounded-full shadow-xl hover:scale-105 transition-all"
                    >
                        {t('landingGoToHome')}
                    </button>
                </SignedIn>
            </section>

            <footer className="w-full py-6 flex flex-col md:flex-row justify-between items-center bg-black/80 border-t border-purple-900 z-20 px-8">
                <span className="text-gray-500 text-sm">© {new Date().getFullYear()} {t('appName')}. {t('copyright')}</span>
                <div className="flex space-x-4 mt-2 md:mt-0">
                    <a href="mailto:azk2021@nyu.edu?subject=Hello&body=I wanted to reach out..." className="text-purple-400 hover:text-purple-200 transition-colors">{t('contact')}</a>
                    <button
                        onClick={() => window.location.href = '/terms'}
                        className="text-purple-400 hover:text-purple-200 transition-colors"
                    >
                        {t('termsOfService')}
                    </button>
                    <button
                        onClick={() => window.location.href = '/privacy'}
                        className="text-purple-400 hover:text-purple-200 transition-colors"
                    >
                        {t('privacyPolicy')}
                    </button>
                </div>
            </footer>
        </div>
    );
} 