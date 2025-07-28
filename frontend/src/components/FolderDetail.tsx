import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import VideoPlayerModal from './VideoPlayerModal';
import { apiUrl } from '../config';
import { t } from '../lib/i18n';

interface Clip {
    id: string;
    blob_url: string;
    title?: string;
    start_time: number;
    end_time: number;
    duration: number;
    created_at: string;
    thumbnail_url?: string;
}

interface VideoDetail {
    id: string;
    youtube_id: string;
    title: string;
    status: string;
    created_at: string;
    clips: Clip[];
}

const FolderDetail = () => {
    const { getToken } = useAuth();
    const [video, setVideo] = useState<VideoDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [, forceUpdate] = useState({});

    // Listen for language changes to re-render
    useEffect(() => {
        const handleLanguageChange = () => {
            forceUpdate({});
        };

        window.addEventListener('languageChanged', handleLanguageChange);
        return () => window.removeEventListener('languageChanged', handleLanguageChange);
    }, []);

    // Get folder ID from URL
    const folderId = window.location.pathname.split('/clips/')[1];

    useEffect(() => {
        if (folderId) {
            fetchFolderDetail();
        }
    }, [folderId]);

    const fetchFolderDetail = async () => {
        try {
            const token = await getToken({ template: "cliplink" });

            const response = await fetch(apiUrl(`/api/videos/${folderId}`), {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch folder details: ${response.status}`);
            }

            const data = await response.json();

            // Log warnings for missing metadata in clips
            if (data.clips && Array.isArray(data.clips)) {
                data.clips.forEach((clip: any, index: number) => {
                    if (!clip.title) {
                        console.warn(`⚠️ Clip ${index + 1} (ID: ${clip.id}) is missing title. Using fallback.`);
                    }
                    if (!clip.thumbnail_url) {
                        console.warn(`⚠️ Clip ${index + 1} (ID: ${clip.id}) is missing thumbnail_url. Thumbnail will not be displayed.`);
                    }
                    if (clip.duration === null || clip.duration === undefined) {
                        console.warn(`⚠️ Clip ${index + 1} (ID: ${clip.id}) is missing duration. Using calculated duration.`);
                    }
                });
            }

            setVideo(data);
            setLoading(false);
        } catch (err) {
            console.error('Error fetching folder details:', err);
            setError(err instanceof Error ? err.message : 'Failed to fetch folder details');
            setLoading(false);
        }
    };

    const handleClipClick = (clip: Clip) => {
        setSelectedClip(clip);
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setSelectedClip(null);
    };

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">{t('loadingClips')}</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="text-red-500 text-xl mb-4">⚠️</div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-2">{t('errorLoadingClips')}</h2>
                    <p className="text-gray-600 mb-4">{error}</p>
                    <div className="space-x-4">
                        <button
                            onClick={fetchFolderDetail}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                        >
                            {t('errorTryAgain')}
                        </button>
                        <button
                            onClick={() => window.location.href = '/clips'}
                            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                        >
                            Back to Folders
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!video) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="text-gray-400 text-4xl mb-4">📁</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Folder not found</h3>
                    <button
                        onClick={() => window.location.href = '/clips'}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        Back to Folders
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    {/* Header */}
                    <div className="mb-8">
                        <button
                            onClick={() => window.location.href = '/clips'}
                            className="flex items-center text-blue-600 hover:text-blue-800 mb-4"
                        >
                            <span className="mr-2">←</span>
                            Back to Folders
                        </button>
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">{video.title}</h1>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                            <span>YouTube ID: {video.youtube_id}</span>
                            <span>•</span>
                            <span>{video.clips.length} clips</span>
                            <span>•</span>
                            <span>Created {new Date(video.created_at).toLocaleDateString()}</span>
                        </div>
                    </div>

                    {/* Clips Grid */}
                    {video.clips.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="text-gray-400 text-4xl mb-4">✂️</div>
                            <h3 className="text-lg font-medium text-gray-900 mb-2">{t('noClipsYet')}</h3>
                            <p className="text-gray-600">
                                {t('noClipsInFolder')}
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {video.clips.map((clip, index) => (
                                <div
                                    key={clip.id}
                                    onClick={() => handleClipClick(clip)}
                                    className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer overflow-hidden"
                                >
                                    {/* Thumbnail */}
                                    <div className="aspect-[3/4] bg-gray-200 flex items-center justify-center relative">
                                        {clip.thumbnail_url ? (
                                            <img
                                                src={clip.thumbnail_url}
                                                alt={`Clip ${index + 1}`}
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <div className="text-gray-400 text-4xl">🎬</div>
                                        )}
                                        <div className="absolute top-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                                            {formatDuration(clip.duration)}
                                        </div>
                                    </div>

                                    {/* Content */}
                                    <div className="p-4">
                                        <h3 className="font-semibold text-gray-900 mb-2">
                                            {clip.title || `Clip ${index + 1}`}
                                        </h3>
                                        <div className="text-sm text-gray-600 space-y-1">
                                            <div>
                                                Time: {formatDuration(clip.start_time)} - {formatDuration(clip.end_time)}
                                            </div>
                                            <div>
                                                Duration: {formatDuration(clip.duration || (clip.end_time - clip.start_time))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Video Player Modal */}
            {selectedClip && (
                <VideoPlayerModal
                    isOpen={isModalOpen}
                    onClose={closeModal}
                    clip={{
                        ...selectedClip,
                        title: `Clip from ${video.title}`
                    }}
                />
            )}
        </div>
    );
};

export default FolderDetail; 