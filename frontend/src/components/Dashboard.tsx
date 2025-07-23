import { useUser, useAuth } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';
import VideoProcessor from './VideoProcessor';
import { getPendingUrl, clearPendingUrl } from './landing';
import { apiUrl, config } from '../config';

interface UserData {
    id: string;
    clerk_id: string;
    email: string;
    first_name?: string;
    last_name?: string;
    created_at: string;
    updated_at: string;
}

interface UserStats {
    total_videos: number;
    total_clips: number;
    videos_processing: number;
    videos_completed: number;
    videos_failed: number;
}

const Dashboard = () => {
    const { user } = useUser();
    const { getToken } = useAuth();
    const [userData, setUserData] = useState<UserData | null>(null);
    const [userStats, setUserStats] = useState<UserStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [pendingUrl, setPendingUrl] = useState<string>('');

    // Check for pending URL from landing page
    useEffect(() => {
        const savedUrl = getPendingUrl();
        if (savedUrl) {
            console.log('🔗 Found pending URL from landing page:', savedUrl);
            setPendingUrl(savedUrl);
            clearPendingUrl(); // Clear it so it doesn't persist
        }
    }, []);

    // Fetch user data from backend
    const fetchUserData = async () => {
        try {
            const token = await getToken({ template: "cliplink" });
            console.log('🔑 Got token, making API call to backend...');

            const response = await fetch(apiUrl('/api/users/me'), {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ User data received from backend:', data);
            setUserData(data);

        } catch (err) {
            console.error('❌ Error fetching user data:', err);
            setError(err instanceof Error ? err.message : 'Failed to fetch user data');
        }
    };

    // Fetch user statistics
    const fetchUserStats = async () => {
        try {
            const token = await getToken({ template: "cliplink" });
            console.log('📊 Fetching user stats...');

            const response = await fetch(apiUrl('/api/users/me/stats'), {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Stats API Error: ${response.status}`);
            }

            const stats = await response.json();
            console.log('✅ User stats received:', stats);
            setUserStats(stats);

        } catch (err) {
            console.error('❌ Error fetching user stats:', err);
            // Don't set error for stats, just log it
        }
    };

    // Test dashboard endpoint
    const testDashboard = async () => {
        try {
            const token = await getToken({ template: "cliplink" });
            console.log('🏠 Testing dashboard endpoint...');

            const response = await fetch(apiUrl('/api/users/dashboard'), {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const dashboardData = await response.json();
                console.log('✅ Dashboard test successful:', dashboardData);
            }

        } catch (err) {
            console.error('❌ Dashboard test failed:', err);
        }
    };

    useEffect(() => {
        const initializeDashboard = async () => {
            if (user) {
                setLoading(true);
                setError(null);

                // Make multiple API calls to test the backend
                await fetchUserData();
                await fetchUserStats();
                await testDashboard();

                setLoading(false);
            }
        };

        initializeDashboard();
    }, [user]); // Only run when user changes

    // const refreshStats = async () => {
    //     await fetchUserStats();
    // };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading dashboard...</p>
                    <p className="text-sm text-gray-500">Making API calls to backend...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">
                                Welcome back{user?.firstName ? `, ${user.firstName}` : ''}! 👋
                            </h1>
                            <p className="text-gray-600 mt-1">Manage your videos and clips</p>
                        </div>
                        {userStats && (
                            <div className="text-right">
                                <div className="text-2xl font-bold text-blue-600">{userStats.total_clips}</div>
                                <div className="text-sm text-gray-500">Total Clips</div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Quick Actions */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                    {/* Process New Video Card */}
                    <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white cursor-pointer hover:shadow-lg transition-shadow"
                        onClick={() => window.location.href = '/process'}>
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-semibold mb-2">🎬 Process New Video</h3>
                                <p className="text-blue-100 text-sm">Transform YouTube videos into viral vertical clips</p>
                            </div>
                            <div className="text-3xl">→</div>
                        </div>
                        <div className="mt-4 text-xs text-blue-100">
                            ✨ AI-powered • 📱 Vertical format • 📝 Auto subtitles
                        </div>
                    </div>

                    {/* Your Videos Card */}
                    <div className="bg-white rounded-lg p-6 shadow-sm border cursor-pointer hover:shadow-md transition-shadow"
                        onClick={() => window.location.href = '/clips'}>
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-semibold mb-2 text-gray-900">📁 Your Videos</h3>
                                <p className="text-gray-600 text-sm">Browse and manage your processed videos</p>
                            </div>
                            <div className="text-2xl text-gray-400">→</div>
                        </div>
                        {userStats && (
                            <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
                                <span>{userStats.total_videos} videos</span>
                                <span>•</span>
                                <span>{userStats.total_clips} clips</span>
                            </div>
                        )}
                    </div>

                    {/* Quick Stats Card */}
                    <div className="bg-white rounded-lg p-6 shadow-sm border">
                        <h3 className="text-lg font-semibold mb-4 text-gray-900">📊 Quick Stats</h3>
                        {userStats ? (
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Processing</span>
                                    <span className="font-medium text-orange-600">{userStats.videos_processing}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Completed</span>
                                    <span className="font-medium text-green-600">{userStats.videos_completed}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Failed</span>
                                    <span className="font-medium text-red-600">{userStats.videos_failed}</span>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center text-gray-500">Loading stats...</div>
                        )}
                    </div>
                </div>

                {/* Video Processor Component */}
                <VideoProcessor
                    initialUrl={pendingUrl}
                />

                {/* User Profile Info */}
                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="px-4 py-5 sm:p-6">
                        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                            Account Information
                        </h3>
                        {userData ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <span className="text-sm font-medium text-gray-500">Email:</span>
                                    <p className="text-sm text-gray-900">{userData.email}</p>
                                </div>
                                <div>
                                    <span className="text-sm font-medium text-gray-500">Name:</span>
                                    <p className="text-sm text-gray-900">
                                        {userData.first_name || userData.last_name
                                            ? `${userData.first_name || ''} ${userData.last_name || ''}`.trim()
                                            : 'Not provided'
                                        }
                                    </p>
                                </div>
                                <div>
                                    <span className="text-sm font-medium text-gray-500">Member Since:</span>
                                    <p className="text-sm text-gray-900">
                                        {new Date(userData.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <p className="text-gray-500">Loading account information...</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard; 