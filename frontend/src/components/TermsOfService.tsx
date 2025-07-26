import { useEffect } from 'react';

const TermsOfService = () => {
    useEffect(() => {
        document.title = 'Terms of Service | Cliplink';
    }, []);

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center py-4">
                        <div className="flex items-center space-x-6">
                            <button
                                onClick={() => window.location.href = '/'}
                                className="text-xl font-semibold text-gray-900 hover:text-blue-600 transition-colors"
                            >
                                Cliplink AI
                            </button>
                        </div>
                        <button
                            onClick={() => window.location.href = '/'}
                            className="text-gray-600 hover:text-gray-900 transition-colors"
                        >
                            ← Back to Home
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="bg-white rounded-lg shadow-sm border p-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
                    <p className="text-gray-600 mb-8">Last Updated: July 26, 2025</p>

                    {/* Table of Contents */}
                    <div className="bg-gray-50 p-6 rounded-lg mb-8">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Table of Contents</h2>
                        <nav className="space-y-2">
                            <a href="#introduction" className="block text-blue-600 hover:text-blue-800 transition-colors">1. Introduction and Acceptance of Terms</a>
                            <a href="#service-description" className="block text-blue-600 hover:text-blue-800 transition-colors">2. Service Description</a>
                            <a href="#user-accounts" className="block text-blue-600 hover:text-blue-800 transition-colors">3. User Accounts and Registration</a>
                            <a href="#acceptable-use" className="block text-blue-600 hover:text-blue-800 transition-colors">4. Acceptable Use Policy</a>
                            <a href="#intellectual-property" className="block text-blue-600 hover:text-blue-800 transition-colors">5. Intellectual Property Rights</a>
                            <a href="#privacy-data" className="block text-blue-600 hover:text-blue-800 transition-colors">6. Privacy and Data Protection</a>
                            <a href="#service-availability" className="block text-blue-600 hover:text-blue-800 transition-colors">7. Service Availability and Modifications</a>
                            <a href="#modifications" className="block text-blue-600 hover:text-blue-800 transition-colors">8. Modifications to Terms</a>
                            <a href="#general-provisions" className="block text-blue-600 hover:text-blue-800 transition-colors">9. General Provisions</a>
                            <a href="#contact" className="block text-blue-600 hover:text-blue-800 transition-colors">10. Contact Information</a>
                        </nav>
                    </div>

                    {/* Terms Content */}
                    <div className="prose prose-gray max-w-none">
                        <section id="introduction" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Introduction and Acceptance of Terms</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <p>Welcome to Cliplink.pro ("Cliplink," "we," "us," or "our"). These Terms of Service ("Terms," "Agreement") constitute a legally binding agreement between you ("User," "you," or "your") and Cliplink.pro regarding your access to and use of our AI-powered platform that generates short viral clips optimized for TikTok from YouTube videos.</p>
                                <p>By accessing, browsing, or using Cliplink in any manner, you acknowledge that you have read, understood, and agree to be bound by these Terms and our Privacy Policy. If you do not agree to these Terms, you must immediately discontinue use of our platform.</p>
                            </div>
                        </section>

                        <section id="service-description" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Service Description</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <p>Cliplink is an artificial intelligence-powered platform that:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Analyzes YouTube videos provided by users</li>
                                    <li>Automatically generates up to 10 short-form video clips optimized for TikTok and other social media platforms</li>
                                    <li>Utilizes advanced AI algorithms to identify engaging segments and optimize content for viral potential</li>
                                    <li>Temporarily stores generated clips in secure Azure Blob Storage infrastructure</li>
                                    <li>Provides users with downloadable clips in various formats suitable for social media distribution</li>
                                </ul>
                                <p>Our service is provided on a free basis with limited numbers of requests in a month for a user.</p>
                            </div>
                        </section>

                        <section id="user-accounts" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. User Accounts and Registration</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">3.1 Account Creation</h3>
                                <p>To access Cliplink's services, you must create an account by:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Providing a valid email address and secure password, or</li>
                                    <li>Authenticating through Google OAuth integration</li>
                                    <li>All authentication is managed through Clerk's secure authentication system</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">3.2 Account Security</h3>
                                <p>You are responsible for:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Maintaining the confidentiality of your login credentials</li>
                                    <li>All activities that occur under your account</li>
                                    <li>Immediately notifying us of any unauthorized access or security breaches</li>
                                    <li>Providing accurate and up-to-date account information</li>
                                </ul>

                            </div>
                        </section>

                        <section id="acceptable-use" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Acceptable Use Policy</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">4.1 Permitted Uses</h3>
                                <p>You may use Cliplink solely for:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Creating short-form content for legitimate personal or commercial purposes</li>
                                    <li>Generating clips from published YouTube videos</li>
                                    <li>Educational, entertainment, or marketing purposes in compliance with applicable laws</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">4.2 Prohibited Uses</h3>
                                <p>You agree NOT to use Cliplink for:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Generating clips containing hate speech, harassment, or discriminatory content</li>
                                    <li>Producing content that promotes violence, illegal activities, or harmful behavior</li>
                                    <li>Creating sexually explicit, pornographic, or adult content involving minors</li>
                                    <li>Reverse engineering, decompiling, or attempting to extract our proprietary algorithms</li>
                                    <li>Using automated tools to access the platform without express written permission</li>
                                    <li>Violating any applicable local, state, national, or international laws</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">4.3 Content Standards</h3>
                                <p>All generated clips must comply with:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>YouTube's Terms of Service and Community Guidelines</li>
                                    <li>TikTok's Community Guidelines and Terms of Service</li>
                                    <li>Applicable copyright and intellectual property laws</li>
                                    <li>Platform-specific content policies where clips will be distributed</li>
                                </ul>
                            </div>
                        </section>

                        <section id="intellectual-property" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Intellectual Property Rights</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">5.1 Cliplink's Intellectual Property</h3>
                                <p>Cliplink retains all rights, title, and interest in:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>The platform, software, and underlying AI technology</li>
                                    <li>All proprietary algorithms, methodologies, and processes</li>
                                    <li>Trademarks, service marks, logos, and brand elements</li>
                                    <li>All improvements, modifications, and derivative works of our technology</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">5.2 Third-Party Rights</h3>
                                <p>Users must respect all third-party intellectual property rights, including but not limited to:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>YouTube content creators' rights</li>
                                    <li>Music licensing and synchronization rights</li>
                                    <li>Trademark and publicity rights</li>
                                </ul>
                            </div>
                        </section>

                        <section id="privacy-data" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Privacy and Data Protection</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">6.1 Data Collection and Use</h3>
                                <p>Our collection, use, and protection of your personal information is governed by our Privacy Policy, which is incorporated into these Terms by reference.</p>

                                <h3 className="text-lg font-semibold text-gray-800">6.2 Temporary Storage</h3>
                                <p>Generated clips are temporarily stored in secure Azure Blob Storage and are automatically deleted after a specified retention period as outlined in our Privacy Policy.</p>

                                <h3 className="text-lg font-semibold text-gray-800">6.3 User Data Rights</h3>
                                <p>You have the right to:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Access your personal data</li>
                                    <li>Request correction of inaccurate information</li>
                                    <li>Request deletion of your account and associated data</li>
                                    <li>Export your data in portable formats where technically feasible</li>
                                </ul>
                            </div>
                        </section>

                        <section id="service-availability" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Service Availability and Modifications</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">7.1 Service Availability</h3>
                                <p>While we strive to maintain continuous service availability, Cliplink may experience downtime for:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Scheduled maintenance and updates</li>
                                    <li>Emergency repairs or security patches</li>
                                    <li>Third-party service provider outages</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">7.2 Service Modifications</h3>
                                <p>We reserve the right to modify, suspend, or discontinue any aspect of our service with reasonable notice to users.</p>
                            </div>
                        </section>

                        <section id="modifications" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Modifications to Terms</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">8.1 Updates</h3>
                                <p>We reserve the right to modify these Terms at any time. Material changes will be communicated through:</p>
                                <ul className="list-disc list-inside space-y-2 ml-4">
                                    <li>Email notifications to registered users</li>
                                    <li>Prominent notices on our platform</li>
                                    <li>Updated "Last Modified" date at the top of these Terms</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">8.2 Continued Use</h3>
                                <p>Your continued use of Cliplink after changes to these Terms constitutes acceptance of the modified Terms.</p>
                            </div>
                        </section>

                        <section id="general-provisions" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. General Provisions</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">9.1 Entire Agreement</h3>
                                <p>These Terms, together with our Privacy Policy, constitute the entire agreement between you and Cliplink regarding use of our platform.</p>

                                <h3 className="text-lg font-semibold text-gray-800">9.2 Severability</h3>
                                <p>If any provision of these Terms is found to be unenforceable, the remaining provisions shall remain in full force and effect.</p>

                                <h3 className="text-lg font-semibold text-gray-800">9.3 Assignment</h3>
                                <p>You may not assign your rights under these Terms without our written consent. We may assign our rights at any time without notice.</p>

                                <h3 className="text-lg font-semibold text-gray-800">9.4 Force Majeure</h3>
                                <p>Cliplink shall not be liable for any failure to perform due to circumstances beyond our reasonable control, including natural disasters, government actions, or third-party service failures.</p>
                            </div>
                        </section>

                        <section id="contact" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">10. Contact Information</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <p>For questions about these Terms or our services, please contact us:</p>
                                <div className="bg-gray-50 p-4 rounded-lg">
                                    <p><strong>Email:</strong> <a href="mailto:azk2021@nyu.edu" className="text-blue-600 hover:text-blue-800">azk2021@nyu.edu</a></p>
                                    <p><strong>Response Time:</strong> We aim to respond to all inquiries within 24 hours during business days.</p>
                                </div>
                                <p>For technical support, legal inquiries, or account-related issues, please use the contact methods provided above.</p>
                                <p className="font-semibold">By using Cliplink.pro, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service.</p>
                            </div>
                        </section>
                    </div>

                    {/* Footer note */}
                    <div className="mt-12 pt-8 border-t border-gray-200">
                        <p className="text-sm text-gray-500">
                            Last updated: July 26, 2025
                        </p>
                    </div>
                </div>
            </main>

            {/* Footer */}
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
                            <button
                                onClick={() => window.location.href = '/terms'}
                                className="text-blue-600 hover:text-blue-800 transition-colors text-sm"
                            >
                                Terms of Service
                            </button>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default TermsOfService; 