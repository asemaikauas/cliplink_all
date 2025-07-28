import React, { useState, useEffect } from 'react';
import type { Language } from '../../lib/i18n';
import { getCurrentLanguage, setLanguage } from '../../lib/i18n';

interface LanguageSelectorProps {
    className?: string;
    variant?: 'default' | 'compact' | 'prominent';
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
    className = '',
    variant = 'default'
}) => {
    const [currentLang, setCurrentLang] = useState<Language>(getCurrentLanguage());
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        const handleLanguageChange = (event: Event) => {
            const customEvent = event as CustomEvent<Language>;
            setCurrentLang(customEvent.detail);
        };

        window.addEventListener('languageChanged', handleLanguageChange);
        return () => window.removeEventListener('languageChanged', handleLanguageChange);
    }, []);

    const handleLanguageChange = (lang: Language) => {
        setLanguage(lang);
        setIsOpen(false);
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.language-selector')) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const languages = [
        {
            code: 'en' as Language,
            name: 'English',
            flag: '🇺🇸',
            shortName: 'EN'
        },
        {
            code: 'ru' as Language,
            name: 'Русский',
            flag: '🇷🇺',
            shortName: 'RU'
        }
    ];

    const currentLanguage = languages.find(lang => lang.code === currentLang);

    if (variant === 'compact') {
        return (
            <div className={`flex items-center space-x-1 ${className}`}>
                {languages.map((lang) => (
                    <button
                        key={lang.code}
                        onClick={() => handleLanguageChange(lang.code)}
                        className={`flex items-center space-x-1 px-2 py-1 text-xs font-medium rounded transition-all duration-200 ${currentLang === lang.code
                                ? 'bg-purple-100 text-purple-700 border border-purple-300'
                                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                            }`}
                        title={lang.name}
                    >
                        <span className="text-sm">{lang.flag}</span>
                        <span className="font-semibold">{lang.shortName}</span>
                    </button>
                ))}
            </div>
        );
    }

    if (variant === 'prominent') {
        return (
            <div className={`relative language-selector ${className}`}>
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                    <span className="text-lg">{currentLanguage?.flag}</span>
                    <span className="font-medium text-gray-700">{currentLanguage?.name}</span>
                    <svg
                        className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''
                            }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {isOpen && (
                    <div className="absolute top-full left-0 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
                        {languages.map((lang) => (
                            <button
                                key={lang.code}
                                onClick={() => handleLanguageChange(lang.code)}
                                className={`w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors duration-150 ${currentLang === lang.code ? 'bg-purple-50 text-purple-700' : 'text-gray-700'
                                    }`}
                            >
                                <span className="text-lg">{lang.flag}</span>
                                <span className="font-medium">{lang.name}</span>
                                {currentLang === lang.code && (
                                    <svg className="w-4 h-4 ml-auto text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                )}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    // Default variant
    return (
        <div className={`flex items-center bg-gray-100 rounded-lg p-1 ${className}`}>
            {languages.map((lang) => (
                <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang.code)}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 ${currentLang === lang.code
                        ? 'bg-white text-purple-700 shadow-sm border border-purple-200'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                        }`}
                    title={lang.name}
                >
                    <span className="text-base">{lang.flag}</span>
                    <span>{lang.shortName}</span>
                </button>
            ))}
        </div>
    );
};

export default LanguageSelector; 