import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiUrl } from '../config';

interface VideoFolder {
    id: string;
    youtube_id: string;
    title: string;
    clips_count: number;
    created_at: string;
    thumbnail_url?: string;
    first_clip_thumbnail?: string;
}

const ClipsFolders = () => {
    const { getToken } = useAuth();
    const [folders, setFolders] = useState<VideoFolder[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchFolders();
    }, []);

    const fetchFolders = async () => {
        try {
            const token = await getToken({ template: "cliplink" });

            const response = await fetch(apiUrl('/api/videos'), {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch folders: ${response.status}`);
            }

            const data = await response.json();
            setFolders(data.videos || []);
            setLoading(false);
        } catch (err) {
            console.error('Error fetching folders:', err);
            setError(err instanceof Error ? err.message : 'Failed to fetch folders');
            setLoading(false);
        }
    };

    const handleFolderClick = (folderId: string) => {
        window.location.href = `/clips/${folderId}`;
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading your clip folders...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="text-red-500 text-xl mb-4">⚠️</div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Folders</h2>
                    <p className="text-gray-600 mb-4">{error}</p>
                    <button
                        onClick={fetchFolders}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    <div className="mb-8">
                        <h1 className="text-2xl font-bold text-gray-900">Your Clip Folders</h1>
                        <p className="mt-2 text-sm text-gray-600">
                            Each folder contains clips generated from a YouTube video
                        </p>
                    </div>

                    {folders.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="text-gray-400 text-4xl mb-4">📁</div>
                            <h3 className="text-lg font-medium text-gray-900 mb-2">No clip folders yet</h3>
                            <p className="text-gray-600 mb-4">
                                Start by creating some clips from a YouTube video
                            </p>
                            <button
                                onClick={() => window.location.href = '/dashboard'}
                                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                            >
                                Go to Home
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {folders.map((folder) => (
                                <div
                                    key={folder.id}
                                    onClick={() => handleFolderClick(folder.id)}
                                    className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer overflow-hidden"
                                >
                                    {/* Thumbnail */}
                                    <div className="aspect-video bg-gray-200 flex items-center justify-center">
                                        {folder.first_clip_thumbnail ? (
                                            <img
                                                src={folder.first_clip_thumbnail}
                                                alt={folder.title}
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <div className="text-gray-400 text-4xl">🎬</div>
                                        )}
                                    </div>

                                    {/* Content */}
                                    <div className="p-4">
                                        <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                                            {folder.title}
                                        </h3>
                                        <div className="flex items-center justify-between text-sm text-gray-600">
                                            <span className="flex items-center">
                                                <span className="mr-1">✂️</span>
                                                {folder.clips_count} clips
                                            </span>
                                            <span>
                                                {new Date(folder.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ClipsFolders; 