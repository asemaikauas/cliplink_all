export type Language = 'en' | 'ru';

export interface LocalizedText {
    en: string;
    ru: string;
}

// Global app texts
export const translations = {
    // App branding
    appName: {
        en: "ClipLink",
        ru: "ClipLink"
    },
    appTagline: {
        en: "Cliplink AI",
        ru: "Cliplink AI"
    },

    // Landing page
    landingHeadline: {
        en: "Instantly Go Viral",
        ru: "Стань вирусным за секунды"
    },
    landingSubtitle: {
        en: "Turn any long video into up to 10 viral clips for Shorts, TikTok, and Reels. No editing. No hassle. Just a link.",
        ru: "Превращай любое длинное видео в 10 вирусных клипов для Shorts, TikTok и Reels. Без монтажа. Без заморочек. Просто ссылка."
    },
    landingInputPlaceholder: {
        en: "Paste YouTube Link Here..",
        ru: "Вставьте YouTube ссылку сюда.."
    },
    landingCTA: {
        en: "Get free clips",
        ru: "Получить видео бесплатно"
    },
    landingSubCTA: {
        en: "No signup required. 100% free to start.",
        ru: "Оплата не нужна. 100% бесплатно для начала."
    },
    landingTryNow: {
        en: "Try ClipLink Now",
        ru: "Попробовать ClipLink"
    },
    landingGoToHome: {
        en: "Go to Home",
        ru: "На главную"
    },

    // Features
    featureAITitle: {
        en: "AI-Powered Editing",
        ru: "Быстрый монтаж"
    },
    featureAIDesc: {
        en: "Let AI find the best moments and create viral clips for you.",
        ru: "ИИ сам подберет самые лучшие моменты видео и создаст вирусные короткие Тик-Ток видео за тебя."
    },
    featureEasyTitle: {
        en: "Nothing Needed",
        ru: "Ничего не нужно"
    },
    featureEasyDesc: {
        en: "Just drop a link. No editing or technical skills required.",
        ru: "Просто скинь ссылку. Никаких навыков монтажа или технических знаний."
    },
    featureFastTitle: {
        en: "Fast & Free",
        ru: "Быстро и бесплатно"
    },
    featureFastDesc: {
        en: "Get up to 10 clips in seconds. Start for free.",
        ru: "Получи до 10 клипов за секунды. Начни бесплатно."
    },

    // Navigation
    navSignIn: {
        en: "Sign In",
        ru: "Войти"
    },
    navDashboard: {
        en: "Dashboard",
        ru: "Главная"
    },
    navMyVideos: {
        en: "My Videos",
        ru: "Мои видео"
    },

    // Dashboard
    dashboardWelcome: {
        en: "Welcome back",
        ru: "С возвращением"
    },
    dashboardTotalClips: {
        en: "Total Clips",
        ru: "Всего клипов"
    },
    dashboardYourVideos: {
        en: "Your Videos",
        ru: "Ваши видео"
    },
    dashboardQuickStats: {
        en: "Quick Stats",
        ru: "Быстрая статистика"
    },
    dashboardProcessing: {
        en: "Processing",
        ru: "Обрабатывается"
    },
    dashboardCompleted: {
        en: "Completed",
        ru: "Завершено"
    },
    dashboardFailed: {
        en: "Failed",
        ru: "Ошибка"
    },
    dashboardAccountInfo: {
        en: "Account Information",
        ru: "Информация об аккаунте"
    },
    dashboardVideosDesc: {
        en: "Browse and manage your processed videos",
        ru: "Просматривайте и управляйте обработанными видео"
    },
    dashboardVideosCount: {
        en: "videos",
        ru: "видео"
    },
    dashboardClipsCount: {
        en: "clips",
        ru: "клипов"
    },

    // Video Processor
    processorTitle: {
        en: "Process YouTube Video",
        ru: "Обработать видео YouTube"
    },
    processorSubtitle: {
        en: "Transform any YouTube video into viral vertical clips with AI-powered analysis and automatic subtitles.",
        ru: "Превратите любое видео YouTube в вирусные вертикальные клипы с анализом ИИ и автоматическими субтитрами."
    },
    processorProgressTitle: {
        en: "Processing Progress",
        ru: "Прогресс обработки"
    },
    processorProgressDesc: {
        en: "Transform YouTube videos into viral vertical clips with AI-powered analysis",
        ru: "Превращайте видео YouTube в вирусные вертикальные клипы с помощью анализа ИИ"
    },
    processorGenerateTitle: {
        en: "Generate Clips from YouTube Video",
        ru: "Создать клипы из видео YouTube"
    },
    processorUrlPlaceholder: {
        en: "Paste YouTube URL here...",
        ru: "Вставьте YouTube ссылку сюда.."
    },
    processorGenerateButton: {
        en: "Generate Clips",
        ru: "Создать клипы"
    },
    processorProcessingButton: {
        en: "Processing...",
        ru: "Обрабатывается..."
    },

    // Authentication
    authRequired: {
        en: "Authentication Required",
        ru: "Требуется авторизация"
    },
    authMessage: {
        en: "Please sign in to process YouTube videos and create clips. Your videos will be saved to your account and accessible across devices.",
        ru: "Пожалуйста, войдите в систему, чтобы обрабатывать видео YouTube и создавать клипы. Ваши видео будут сохранены в аккаунте и доступны на всех устройствах."
    },
    authFeatureSecure: {
        en: "Secure video processing",
        ru: "Безопасная обработка видео"
    },
    authFeatureStorage: {
        en: "Persistent video storage",
        ru: "Постоянное хранение видео"
    },
    authFeatureAccess: {
        en: "Access from any device",
        ru: "Доступ с любого устройства"
    },

    // Status messages
    statusAlmostDone: {
        en: "Almost done!",
        ru: "Почти готово!"
    },
    statusWait: {
        en: "Wait:",
        ru: "Ожидание:"
    },
    statusMinute: {
        en: "min",
        ru: "мин"
    },
    statusReady: {
        en: "Ready! 🎉",
        ru: "Готово! 🎉"
    },
    statusFailed: {
        en: "Failed ❌",
        ru: "Ошибка ❌"
    },

    // ClipsFolders
    clipsTitle: {
        en: "Your Clip Folders",
        ru: "Ваши папки с клипами"
    },
    clipsDesc: {
        en: "Each folder contains clips generated from a YouTube video",
        ru: "Каждая папка содержит клипы, созданные из видео YouTube"
    },
    clipsEmpty: {
        en: "No clip folders yet",
        ru: "Пока нет папок с клипами"
    },
    clipsEmptyDesc: {
        en: "Start by creating some clips from a YouTube video",
        ru: "Начните с создания клипов из видео YouTube"
    },
    clipsGoHome: {
        en: "Go to Home",
        ru: "На главную"
    },
    clipsCount: {
        en: "clips",
        ru: "клипов"
    },

    // Loading states
    loading: {
        en: "Loading...",
        ru: "Загрузка..."
    },
    loadingDashboard: {
        en: "Loading dashboard...",
        ru: "Загружается панель..."
    },
    loadingStats: {
        en: "Loading stats...",
        ru: "Загружается статистика..."
    },
    loadingFolders: {
        en: "Loading your clip folders...",
        ru: "Загружаются ваши папки с клипами..."
    },
    loadingApiCalls: {
        en: "Making API calls to backend...",
        ru: "Отправляются запросы к серверу..."
    },
    loadingClips: {
        en: "Loading clips...",
        ru: "Загружаются клипы..."
    },

    // Errors
    errorGeneral: {
        en: "Error",
        ru: "Ошибка"
    },
    errorLoadingFolders: {
        en: "Error Loading Folders",
        ru: "Ошибка загрузки папок"
    },
    errorLoadingClips: {
        en: "Error Loading Clips",
        ru: "Ошибка загрузки клипов"
    },
    errorTryAgain: {
        en: "Try Again",
        ru: "Попробовать снова"
    },
    errorActiveTask: {
        en: "⚠️ You have an active processing task. Please wait for it to complete before starting a new one.",
        ru: "⚠️ У вас есть активная задача обработки. Пожалуйста, дождитесь её завершения перед запуском новой."
    },
    errorYouTubeUrl: {
        en: "Please enter a YouTube URL first",
        ru: "Сначала введите ссылку на YouTube"
    },

    // Session restoration
    sessionRestoring: {
        en: "Restoring Session",
        ru: "Восстанавливается сессия"
    },
    sessionRestoringDesc: {
        en: "Checking for ongoing video processing...",
        ru: "Проверяется обработка видео..."
    },

    // Contact and legal
    contact: {
        en: "Contact",
        ru: "Контакты"
    },
    termsOfService: {
        en: "Terms of Service",
        ru: "Условия использования"
    },
    privacyPolicy: {
        en: "Privacy Policy",
        ru: "Политика конфиденциальности"
    },
    copyright: {
        en: "All rights reserved.",
        ru: "Все права защищены."
    },

    // Call to action sections
    startForFree: {
        en: "Start for Free",
        ru: "Начать бесплатно"
    },
    noCreditCard: {
        en: "No credit card required. Get your first viral clips in seconds.",
        ru: "Не нужно привязывать карту. Получите первые вирусные клипы за секунды."
    },

    // Account info
    accountEmail: {
        en: "Email:",
        ru: "Эл. почта:"
    },
    accountName: {
        en: "Name:",
        ru: "Имя:"
    },
    accountMemberSince: {
        en: "Member Since:",
        ru: "Участник с:"
    },
    accountNotProvided: {
        en: "Not provided",
        ru: "Не указано"
    },
    accountLoading: {
        en: "Loading account information...",
        ru: "Загружается информация об аккаунте..."
    },

    // Backend API error messages
    apiErrorTimeout: {
        en: "Processing timed out. This can happen with large videos or during intensive operations like vertical cropping.",
        ru: "Время обработки истекло. Это может произойти с большими видео или во время интенсивных операций, таких как вертикальная обрезка."
    },
    apiErrorTimeoutSuggestion: {
        en: "Try processing a shorter video or disable vertical cropping to reduce processing time.",
        ru: "Попробуйте обработать более короткое видео или отключите вертикальную обрезку для уменьшения времени обработки."
    },
    apiErrorVerticalCrop: {
        en: "Vertical cropping failed. This is a CPU-intensive operation that can fail on some systems.",
        ru: "Ошибка вертикальной обрезки. Это ресурсоёмкая операция, которая может не работать на некоторых системах."
    },
    apiErrorVerticalCropSuggestion: {
        en: "Try processing a shorter video or check if your system has sufficient CPU resources.",
        ru: "Попробуйте обработать более короткое видео или проверьте, достаточно ли ресурсов процессора в вашей системе."
    },
    apiErrorMemory: {
        en: "Insufficient memory for video processing.",
        ru: "Недостаточно памяти для обработки видео."
    },
    apiErrorMemorySuggestion: {
        en: "Try processing a shorter video or lower quality setting.",
        ru: "Попробуйте обработать более короткое видео или выберите более низкое качество."
    },
    apiErrorGeneral: {
        en: "Please try again or contact support if the issue persists.",
        ru: "Пожалуйста, попробуйте снова или обратитесь в поддержку, если проблема не исчезнет."
    },
    apiErrorNetwork: {
        en: "Network error. Please check your internet connection.",
        ru: "Ошибка сети. Пожалуйста, проверьте подключение к интернету."
    },
    apiErrorInternalServer: {
        en: "Internal server error",
        ru: "Внутренняя ошибка сервера"
    },
    apiErrorSubtitles: {
        en: "Subtitle processing failed",
        ru: "Ошибка обработки субтитров"
    },
    apiErrorTranscript: {
        en: "Error fetching transcript.",
        ru: "Ошибка получения транскрипции."
    },

    // Processing stages
    stageQueued: {
        en: "Queued",
        ru: "В очереди"
    },
    stageInit: {
        en: "Initializing",
        ru: "Инициализация"
    },
    stageVideoInfo: {
        en: "Getting video info",
        ru: "Получение информации о видео"
    },
    stageDownload: {
        en: "Downloading",
        ru: "Скачивание"
    },
    stageTranscript: {
        en: "Generating transcript",
        ru: "Создание транскрипции"
    },
    stageAnalysis: {
        en: "AI analysis",
        ru: "Анализ ИИ"
    },
    stageParallelProcessing: {
        en: "Creating clips",
        ru: "Создание клипов"
    },
    stageFinalizing: {
        en: "Finalizing",
        ru: "Завершение"
    },
    stageAzureUpload: {
        en: "Uploading",
        ru: "Загрузка"
    },
    stageProcessing: {
        en: "Processing",
        ru: "Обработка"
    },

    // Common actions
    actionDownload: {
        en: "Download",
        ru: "Скачать"
    },
    actionWatch: {
        en: "Watch",
        ru: "Смотреть"
    },
    actionOpen: {
        en: "Open",
        ru: "Открыть"
    },
    actionClose: {
        en: "Close",
        ru: "Закрыть"
    },
    actionClear: {
        en: "Clear",
        ru: "Очистить"
    },
    actionRefresh: {
        en: "Refresh",
        ru: "Обновить"
    },
    actionCancel: {
        en: "Cancel",
        ru: "Отмена"
    },
    actionContinue: {
        en: "Continue",
        ru: "Продолжить"
    },

    // Time and duration
    timeSeconds: {
        en: "sec",
        ru: "сек"
    },
    timeMinutes: {
        en: "min",
        ru: "мин"
    },
    timeHours: {
        en: "hr",
        ru: "ч"
    },

    // Additional UI elements
    transcriptLabel: {
        en: "Transcript:",
        ru: "Транскрипция:"
    },
    clipDuration: {
        en: "Duration:",
        ru: "Длительность:"
    },
    clipStartTime: {
        en: "Start:",
        ru: "Начало:"
    },
    clipEndTime: {
        en: "End:",
        ru: "Конец:"
    },

    // Empty states
    noClipsYet: {
        en: "No clips yet",
        ru: "Пока нет клипов"
    },
    noClipsMessage: {
        en: "Enter a YouTube URL above and click \"Generate Clips\" to get started.",
        ru: "Введите ссылку на YouTube выше и нажмите \"Создать клипы\", чтобы начать."
    },
    noClipsInFolder: {
        en: "Clips from this video will appear here once processing is complete",
        ru: "Клипы из этого видео появятся здесь после завершения обработки"
    }
};

// Current language state
let currentLanguage: Language = 'en';

// Language detection and setting
export const detectLanguage = (): Language => {
    // Priority 1: Check if user explicitly selected a language
    const savedLang = localStorage.getItem('cliplink_language') as Language;
    if (savedLang && (savedLang === 'en' || savedLang === 'ru')) {
        return savedLang;
    }

    // Priority 2: Auto-detect from browser language with better logic
    const browserLang = navigator.language.toLowerCase();
    const browserLangs = navigator.languages || [navigator.language];

    // Check primary language and all browser languages
    for (const lang of browserLangs) {
        const normalizedLang = lang.toLowerCase();

        // Russian language detection - covers various Russian locales
        if (normalizedLang.startsWith('ru') ||
            normalizedLang.includes('ru-') ||
            normalizedLang === 'be' || // Belarusian often uses Russian
            normalizedLang === 'kk' || // Kazakh often uses Russian
            normalizedLang === 'ky' || // Kyrgyz often uses Russian
            normalizedLang === 'uz' || // Uzbek often uses Russian
            normalizedLang === 'uk'    // Ukrainian often understands Russian
        ) {
            return 'ru';
        }
    }

    // Priority 3: Check timezone for additional context (fallback)
    try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const russianTimezones = [
            'Europe/Moscow', 'Europe/Kaliningrad', 'Europe/Samara', 'Europe/Volgograd',
            'Asia/Yekaterinburg', 'Asia/Omsk', 'Asia/Krasnoyarsk', 'Asia/Irkutsk',
            'Asia/Yakutsk', 'Asia/Vladivostok', 'Asia/Magadan', 'Asia/Kamchatka',
            'Asia/Almaty', 'Asia/Bishkek', 'Asia/Tashkent', 'Asia/Dushanbe',
            'Europe/Kiev', 'Europe/Minsk'
        ];

        if (russianTimezones.includes(timezone)) {
            // Don't auto-set based on timezone alone, but use it as a hint
            // We'll use this in the welcome modal to suggest Russian
            localStorage.setItem('cliplink_timezone_suggests_ru', 'true');
        }
    } catch (e) {
        // Timezone detection failed, continue with default
    }

    return 'en'; // Default to English
};

// Get suggested language based on multiple factors
export const getSuggestedLanguage = (): Language => {
    const detectedLang = detectLanguage();

    // If we already detected Russian from browser language, return it
    if (detectedLang === 'ru') {
        return 'ru';
    }

    // Check if timezone suggests Russian
    const timezoneSuggestsRu = localStorage.getItem('cliplink_timezone_suggests_ru');
    if (timezoneSuggestsRu === 'true') {
        return 'ru';
    }

    return 'en';
};

export const setLanguage = (lang: Language) => {
    currentLanguage = lang;
    localStorage.setItem('cliplink_language', lang);
    // You could dispatch an event here for components to re-render
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: lang }));
};

export const getCurrentLanguage = (): Language => {
    return currentLanguage;
};

// Main translation function
export const t = (key: keyof typeof translations): string => {
    const translation = translations[key];
    if (!translation) {
        console.warn(`Translation missing for key: ${key}`);
        return key;
    }
    return translation[currentLanguage] || translation.en;
};

// Initialize language on import
currentLanguage = detectLanguage(); 