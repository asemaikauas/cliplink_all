import { useUser, useAuth } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';
import VideoProcessor from './VideoProcessor';
import { getPendingUrl, clearPendingUrl } from './landing';
import { apiUrl } from '../config';

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

            <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    {error ? (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
                            <h3 className="text-lg font-semibold text-red-800 mb-2">Backend Connection Error</h3>
                            <p className="text-red-600">{error}</p>
                            <p className="text-sm text-red-500 mt-2">
                                Make sure your backend is running on http://localhost:8000
                            </p>
                            <button
                                onClick={() => {
                                    setError(null);
                                    fetchUserData();
                                }}
                                className="mt-3 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                            >
                                Retry
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Welcome Banner */}
                            {pendingUrl && (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                    <div className="flex items-center">
                                        <div className="text-blue-800">
                                            <h4 className="font-medium">Ready to Process Your Video! 🎬</h4>
                                            <p className="text-sm mt-1">
                                                We've pre-filled the URL you submitted. Click "Generate Clips" below to start processing.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* User Stats Row */}
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="bg-white overflow-hidden shadow rounded-lg">
                                    <div className="p-5">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0">
                                                <div className="text-2xl">📹</div>
                                            </div>
                                            <div className="ml-5 w-0 flex-1">
                                                <dl>
                                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                                        Total Videos
                                                    </dt>
                                                    <dd className="text-lg font-medium text-gray-900">
                                                        {userStats ? userStats.total_videos : '...'}
                                                    </dd>
                                                </dl>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white overflow-hidden shadow rounded-lg">
                                    <div className="p-5">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0">
                                                <div className="text-2xl">✂️</div>
                                            </div>
                                            <div className="ml-5 w-0 flex-1">
                                                <dl>
                                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                                        Total Clips
                                                    </dt>
                                                    <dd className="text-lg font-medium text-gray-900">
                                                        {userStats ? userStats.total_clips : '...'}
                                                    </dd>
                                                </dl>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white overflow-hidden shadow rounded-lg">
                                    <div className="p-5">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0">
                                                <div className="text-2xl">⚡</div>
                                            </div>
                                            <div className="ml-5 w-0 flex-1">
                                                <dl>
                                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                                        Processing
                                                    </dt>
                                                    <dd className="text-lg font-medium text-yellow-600">
                                                        {userStats ? userStats.videos_processing : '...'}
                                                    </dd>
                                                </dl>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white overflow-hidden shadow rounded-lg">
                                    <div className="p-5">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0">
                                                <div className="text-2xl">✅</div>
                                            </div>
                                            <div className="ml-5 w-0 flex-1">
                                                <dl>
                                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                                        Completed
                                                    </dt>
                                                    <dd className="text-lg font-medium text-green-600">
                                                        {userStats ? userStats.videos_completed : '...'}
                                                    </dd>
                                                </dl>
                                            </div>
                                        </div>
                                    </div>
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
                    )}
                </div>
            </div>
        </div>
    );
};

export default Dashboard; 