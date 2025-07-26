export const Footer = () => {
    return (
        <footer className="bg-white border-t border-gray-200 mt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex flex-col md:flex-row justify-between items-center">
                    <span className="text-gray-500 text-sm">© {new Date().getFullYear()} ClipLink. All rights reserved.</span>
                    <div className="flex space-x-4 mt-2 md:mt-0">
                        <button
                            onClick={() => window.location.href = '/'}
                            className="text-blue-600 hover:text-blue-800 transition-colors text-sm"
                        >
                            Home
                        </button>
                        <a
                            href="mailto:azk2021@nyu.edu?subject=Hello&body=I wanted to reach out..."
                            className="text-blue-600 hover:text-blue-800 transition-colors text-sm"
                        >
                            Contact
                        </a>
                        <button
                            onClick={() => window.location.href = '/terms'}
                            className="text-blue-600 hover:text-blue-800 transition-colors text-sm"
                        >
                            Terms of Service
                        </button>
                        <button
                            onClick={() => window.location.href = '/privacy'}
                            className="text-blue-600 hover:text-blue-800 transition-colors text-sm"
                        >
                            Privacy Policy
                        </button>
                    </div>
                </div>
            </div>
        </footer>
    );
}; 