import React, { useState, useEffect } from 'react';
import type { Language } from '../../lib/i18n';
import { setLanguage, getSuggestedLanguage } from '../../lib/i18n';

interface LanguageWelcomeModalProps {
    onClose: () => void;
}

const LanguageWelcomeModal: React.FC<LanguageWelcomeModalProps> = ({ onClose }) => {
    const [selectedLanguage, setSelectedLanguage] = useState<Language>(getSuggestedLanguage());

    const languages = [
        {
            code: 'en' as Language,
            name: 'English',
            flag: '🇺🇸',
            description: 'Continue in English',
            greeting: 'Welcome to ClipLink!'
        },
        {
            code: 'ru' as Language,
            name: 'Русский',
            flag: '🇷🇺',
            description: 'Продолжить на русском',
            greeting: 'Добро пожаловать в ClipLink!'
        }
    ];

    const handleLanguageSelect = (lang: Language) => {
        setSelectedLanguage(lang);
        setLanguage(lang);
        // Mark that user has selected language
        localStorage.setItem('cliplink_language_selected', 'true');
        onClose();
    };

    const selectedLang = languages.find(lang => lang.code === selectedLanguage);
    const suggestedLang = getSuggestedLanguage();

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
                {/* Header */}
                <div className="bg-gradient-to-r from-purple-600 to-purple-700 px-6 py-4 text-white">
                    <h2 className="text-xl font-bold text-center">
                        {selectedLang?.greeting}
                    </h2>
                    <p className="text-purple-100 text-center text-sm mt-1">
                        Choose your preferred language
                    </p>
                </div>

                {/* Language Options */}
                <div className="p-6">
                    <div className="space-y-3">
                        {languages.map((lang) => (
                            <button
                                key={lang.code}
                                onClick={() => handleLanguageSelect(lang.code)}
                                className={`w-full flex items-center space-x-4 p-4 rounded-xl border-2 transition-all duration-200 hover:shadow-md ${selectedLanguage === lang.code
                                        ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200'
                                        : 'border-gray-200 hover:border-purple-300 hover:bg-gray-50'
                                    }`}
                            >
                                <span className="text-3xl">{lang.flag}</span>
                                <div className="flex-1 text-left">
                                    <div className="flex items-center space-x-2">
                                        <span className="font-semibold text-gray-900">{lang.name}</span>
                                        {lang.code === suggestedLang && (
                                            <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
                                                Suggested
                                            </span>
                                        )}
                                    </div>
                                    <div className="text-sm text-gray-600">{lang.description}</div>
                                </div>
                                {selectedLanguage === lang.code && (
                                    <div className="text-purple-600">
                                        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>

                    {/* Info */}
                    <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                        <div className="flex items-start space-x-3">
                            <div className="text-blue-500 mt-0.5">
                                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="text-sm text-blue-800">
                                <div className="font-medium">You can change this later</div>
                                <div className="text-blue-600">
                                    Use the language switcher in the top navigation anytime.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Hook to show language welcome modal
export const useLanguageWelcome = () => {
    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        const hasSelectedLanguage = localStorage.getItem('cliplink_language_selected');

        // Show modal if user hasn't explicitly selected a language
        if (!hasSelectedLanguage) {
            // Small delay to ensure everything is loaded
            const timer = setTimeout(() => {
                setShowModal(true);
            }, 500);

            return () => clearTimeout(timer);
        }
    }, []);

    const closeModal = () => {
        setShowModal(false);
        localStorage.setItem('cliplink_language_selected', 'true');
    };

    return { showModal, closeModal };
};

export default LanguageWelcomeModal; 