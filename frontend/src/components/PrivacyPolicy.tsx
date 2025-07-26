import { useEffect } from 'react';

const PrivacyPolicy = () => {
    useEffect(() => {
        document.title = 'Privacy Policy | Cliplink';
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
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
                    <p className="text-gray-600 mb-8">Last Updated: July 26, 2025</p>

                    {/* Table of Contents */}
                    <div className="bg-gray-50 p-6 rounded-lg mb-8">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Table of Contents</h2>
                        <nav className="space-y-2">
                            <a href="#introduction" className="block text-blue-600 hover:text-blue-800 transition-colors">1. Introduction</a>
                            <a href="#information-collection" className="block text-blue-600 hover:text-blue-800 transition-colors">2. Information We Collect</a>
                            <a href="#information-use" className="block text-blue-600 hover:text-blue-800 transition-colors">3. How We Use Your Information</a>
                            <a href="#information-sharing" className="block text-blue-600 hover:text-blue-800 transition-colors">4. Information Sharing and Disclosure</a>
                            <a href="#data-security" className="block text-blue-600 hover:text-blue-800 transition-colors">5. Data Security</a>
                            <a href="#data-retention" className="block text-blue-600 hover:text-blue-800 transition-colors">6. Data Retention and Deletion</a>
                            <a href="#privacy-rights" className="block text-blue-600 hover:text-blue-800 transition-colors">7. Your Privacy Rights</a>
                            <a href="#international-transfers" className="block text-blue-600 hover:text-blue-800 transition-colors">8. International Data Transfers</a>
                            <a href="#third-party" className="block text-blue-600 hover:text-blue-800 transition-colors">9. Youtube Integration</a>
                            <a href="#policy-updates" className="block text-blue-600 hover:text-blue-800 transition-colors">10. Privacy Policy Updates</a>
                            <a href="#contact" className="block text-blue-600 hover:text-blue-800 transition-colors">11. Contact Information</a>
                        </nav>
                    </div>

                    {/* Privacy Policy Content */}
                    <div className="prose prose-gray max-w-none">
                        <section id="introduction" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Introduction</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <p>Cliplink.pro ("Cliplink," "we," "our," "us") is committed to protecting your privacy and personal information. This Privacy Policy explains how we collect, use, store, share, and protect your information when you use our AI-powered video clip generation platform ("Service").</p>
                                <p>This Privacy Policy applies to all users of Cliplink.pro and should be read in conjunction with our Terms of Service. By using our Service, you consent to the data practices described in this Privacy Policy.</p>
                            </div>
                        </section>

                        <section id="information-collection" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Information We Collect</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">2.1 Personal Information You Provide</h3>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Account Information:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Email address (required for account creation)</li>
                                            <li>Password (encrypted and managed by Clerk authentication service)</li>
                                            <li>Time you joined platform</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Authentication Data:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Google account information (if you choose Google OAuth login)</li>
                                            <li>Authentication tokens and session data</li>
                                            <li>Account verification status</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Communication Data:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Support requests and correspondence</li>
                                            <li>Feedback and survey responses</li>
                                            <li>Any information you provide when contacting us</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">2.2 Automatically Collected Information</h3>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Usage Data:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Video processing requests and clip generation activity</li>
                                            <li>Generated clips</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Technical Data:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Device type</li>
                                            <li>Log files and error reports</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Content Data:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Generated video clips and thumbnails temporarily for 3 weeks</li>
                                            <li>Clip titles and metadata</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">2.3 Cookies and Tracking Technologies</h3>
                                <p>We use the following technologies to enhance your experience:</p>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Essential Cookies:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Authentication and session management</li>
                                            <li>Security and fraud prevention</li>
                                            <li>Core platform functionality</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Analytics Cookies:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Usage statistics and performance monitoring</li>
                                            <li>Feature adoption and user behavior analysis</li>
                                            <li>Platform optimization insights</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Preference Cookies:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>User interface customizations</li>
                                            <li>Language and regional settings</li>
                                            <li>Processing preferences</li>
                                        </ul>
                                    </div>
                                </div>
                                <p>You can control cookie preferences through your browser settings, though disabling essential cookies may affect platform functionality.</p>
                            </div>
                        </section>

                        <section id="information-use" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. How We Use Your Information</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">3.1 Primary Uses</h3>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Service Delivery:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Authenticate and manage your account</li>
                                            <li>Process YouTube videos and generate clips</li>
                                            <li>Provide customer support and respond to inquiries</li>
                                            <li>Deliver platform features and functionality</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Platform Improvement:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Develop new features and optimize existing ones</li>
                                            <li>Monitor platform performance and reliability</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Communication:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Send important service updates and notifications</li>
                                            <li>Respond to support requests and feedback</li>
                                            <li>Provide technical assistance and troubleshooting</li>
                                            <li>Share relevant product updates (with your consent)</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">3.2 Legal and Security Uses</h3>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Compliance and Legal:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Comply with applicable laws and regulations</li>
                                            <li>Respond to legal requests and court orders</li>
                                            <li>Enforce our Terms of Service and policies</li>
                                            <li>Protect against fraud and abuse</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Security:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Detect and prevent unauthorized access</li>
                                            <li>Monitor for security threats and vulnerabilities</li>
                                            <li>Investigate and respond to security incidents</li>
                                            <li>Maintain platform integrity and stability</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <section id="information-sharing" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Information Sharing and Disclosure</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">4.1 Third-Party Service Providers</h3>
                                <p>We share information with trusted third-party services that help us operate our platform:</p>

                                <div className="bg-gray-50 p-4 rounded-lg space-y-4">
                                    <div>
                                        <h4 className="font-semibold">Clerk (Authentication Service):</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Manages user authentication and account security</li>
                                            <li>Stores encrypted login credentials</li>
                                            <li>Handles password resets and account verification</li>
                                            <li><strong>Data Shared:</strong> Email addresses, authentication tokens, account status</li>
                                            <li><strong>Privacy Policy:</strong> Clerk's Privacy Policy</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Microsoft Azure (Cloud Storage):</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Temporarily stores generated video clips and thumbnails</li>
                                            <li>Provides secure, encrypted cloud infrastructure</li>
                                            <li>Manages data backup and recovery</li>
                                            <li><strong>Data Shared:</strong> Generated clips, thumbnails, processing metadata</li>
                                            <li><strong>Privacy Policy:</strong> Microsoft Privacy Statement</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Google Analytics:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Helps us understand platform usage patterns and performance metrics</li>
                                            <li>Provides insights for product improvement and user experience optimization</li>
                                            <li>Tracks page views, user interactions, and conversion funnels</li>
                                            <li><strong>Data Shared:</strong> Anonymized usage statistics, technical data, user behavior patterns</li>
                                            <li><strong>Privacy Policy:</strong> Google Analytics Privacy Policy</li>
                                            <li><strong>Opt-out:</strong> You can opt-out using the Google Analytics Opt-out Browser Add-on</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">4.2 Legal Disclosures</h3>
                                <p>We may disclose your information when required by law or when we believe in good faith that disclosure is necessary to:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>Comply with legal processes, court orders, or government requests</li>
                                    <li>Protect our rights, property, or safety, or that of our users</li>
                                    <li>Investigate potential violations of our Terms of Service</li>
                                    <li>Prevent or address fraud, security, or technical issues</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">4.3 Business Transfers</h3>
                                <p>In the event of a merger, acquisition, or sale of assets, your information may be transferred as part of the transaction. We will provide notice and ensure continued protection of your data.</p>

                                <h3 className="text-lg font-semibold text-gray-800">4.4 What We Don't Do</h3>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>We never sell your personal data to third parties for marketing purposes</li>
                                    <li>We don't share your content with unauthorized parties</li>
                                    <li>We don't use your data for advertising or marketing without consent</li>
                                </ul>
                            </div>
                        </section>

                        <section id="data-security" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Data Security</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">5.1 Security Measures</h3>
                                <p>We implement industry-standard security practices to protect your information:</p>

                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Technical Safeguards:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>End-to-end encryption for data transmission</li>
                                            <li>Encrypted storage of sensitive information</li>
                                            <li>Regular security audits and vulnerability assessments</li>
                                            <li>Multi-factor authentication for administrative access</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Operational Safeguards:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Access controls limiting data access to authorized personnel</li>
                                            <li>Regular employee security training and awareness programs</li>
                                            <li>Incident response procedures for security breaches</li>
                                            <li>Secure development practices and code reviews</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Physical Safeguards:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Secure data centers with restricted access</li>
                                            <li>Environmental controls and monitoring systems</li>
                                            <li>Backup and disaster recovery procedures</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">5.2 Data Breach Response</h3>
                                <p>In the unlikely event of a data breach, we will:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>Immediately investigate and contain the incident</li>
                                    <li>Notify affected users within 72 hours where required by law</li>
                                    <li>Provide clear information about what data was affected</li>
                                    <li>Take steps to prevent future occurrences</li>
                                </ul>
                            </div>
                        </section>

                        <section id="data-retention" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Data Retention and Deletion</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">6.1 Retention Periods</h3>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Account Data:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Retained for the duration of your active account</li>
                                            <li>Deleted in a day of account closure</li>
                                            <li>Some data may be retained longer for legal compliance</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Generated Content:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Video clips automatically deleted after 21 days from creation</li>
                                            <li>Thumbnails and metadata deleted with associated clips</li>
                                            <li>Processing logs retained for 5 days for troubleshooting</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">6.2 Automated Deletion</h3>
                                <p>Our systems automatically delete:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>Expired video clips and associated data</li>
                                    <li>Temporary processing files immediately after use</li>
                                    <li>Session data upon logout or expiration</li>
                                    <li>Inactive account data after extended periods</li>
                                </ul>
                            </div>
                        </section>

                        <section id="privacy-rights" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Your Privacy Rights</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">7.1 Access and Control</h3>
                                <p>You have the following rights regarding your personal data:</p>

                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Access Rights:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Request a copy of all personal data we hold about you</li>
                                            <li>Receive information about how your data is processed</li>
                                            <li>Access your data in a portable, machine-readable format</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Correction Rights:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Update or correct inaccurate personal information</li>
                                            <li>Complete incomplete data records</li>
                                            <li>Modify your account preferences and settings</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Deletion Rights:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Request deletion of your personal data ("right to be forgotten")</li>
                                            <li>Close your account and remove associated data</li>
                                            <li>Delete specific pieces of information</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Control Rights:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Withdraw consent for data processing activities</li>
                                            <li>Opt out of non-essential communications</li>
                                            <li>Control cookie preferences and tracking</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">7.2 Exercising Your Rights</h3>
                                <p>To exercise your privacy rights:</p>
                                <div className="bg-gray-50 p-4 rounded-lg">
                                    <ul className="list-disc list-inside space-y-1">
                                        <li><strong>Account Settings:</strong> Use in-platform tools for basic data management</li>
                                        <li><strong>Email Request:</strong> Contact us at <a href="mailto:azk2021@nyu.edu" className="text-blue-600 hover:text-blue-800">azk2021@nyu.edu</a> with specific requests</li>
                                        <li><strong>Response Time:</strong> We respond to requests within 30 days</li>
                                        <li><strong>Identity Verification:</strong> We may require verification to protect your privacy</li>
                                    </ul>
                                </div>
                            </div>
                        </section>

                        <section id="international-transfers" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. International Data Transfers</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">8.1 Data Location</h3>
                                <p>Your data may be processed and stored in:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>European Union (primary data centers)</li>
                                    <li>Other regions where our service providers operate</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">8.2 Transfer Safeguards</h3>
                                <p>For international transfers, we ensure adequate protection through:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>Standard Contractual Clauses (SCCs) with service providers</li>
                                    <li>Adequacy decisions by relevant data protection authorities</li>
                                    <li>Additional security measures for sensitive data</li>
                                </ul>
                            </div>
                        </section>



                        <section id="third-party" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. Youtube Integration</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">

                                <p>When you provide YouTube video URLs:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>We only access publicly available video content</li>
                                    <li>No YouTube account linking or authentication required</li>
                                </ul>
                            </div>
                        </section>

                        <section id="policy-updates" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">10. Privacy Policy Updates</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <h3 className="text-lg font-semibold text-gray-800">10.1 Change Notifications</h3>
                                <p>We may update this Privacy Policy to reflect:</p>
                                <ul className="list-disc list-inside space-y-1 ml-4">
                                    <li>Changes in our data practices</li>
                                    <li>New features or services</li>
                                    <li>Legal or regulatory requirements</li>
                                    <li>Industry best practices</li>
                                </ul>

                                <h3 className="text-lg font-semibold text-gray-800">10.2 How We Notify You</h3>
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="font-semibold">Significant Changes:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Email notification to registered users</li>
                                            <li>Prominent notice on our platform</li>
                                            <li>30-day advance notice when possible</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">Minor Changes:</h4>
                                        <ul className="list-disc list-inside space-y-1 ml-4">
                                            <li>Updated "Last Modified" date</li>
                                            <li>Summary of changes in platform notifications</li>
                                        </ul>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-gray-800">10.3 Continued Use</h3>
                                <p>Your continued use of Cliplink after policy updates constitutes acceptance of the changes. If you disagree with updates, you may close your account.</p>
                            </div>
                        </section>

                        <section id="contact" className="mb-8">
                            <h2 className="text-2xl font-semibold text-gray-900 mb-4">11. Contact Information</h2>
                            <div className="text-gray-700 leading-relaxed space-y-4">
                                <p>For questions about these Terms or our services, please contact us:</p>
                                <div className="bg-gray-50 p-4 rounded-lg">
                                    <p><strong>Email:</strong> <a href="mailto:azk2021@nyu.edu" className="text-blue-600 hover:text-blue-800">azk2021@nyu.edu</a></p>
                                    <p><strong>Response Time:</strong> We aim to respond to all inquiries within 24 hours during business days.</p>
                                </div>
                                <p>For technical support, legal inquiries, or account-related issues, please use the contact methods provided above.</p>
                                <p className="font-semibold">By using Cliplink.pro, you acknowledge that you have read, understood, and agree to be bound by this Privacy Policy.</p>
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
        </div>
    );
};

export default PrivacyPolicy; 