import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { UploadDropzone } from '../components/projects/UploadDropzone';
import { useUploadProject } from '../hooks/useProjects';
import { cn } from '../lib/utils';

type Tab = 'upload' | 'url';

const TABS: { id: Tab; label: string }[] = [
  { id: 'upload', label: 'Upload file' },
  { id: 'url', label: 'Paste URL' },
];

export function NewProjectPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  const uploadMutation = useUploadProject();

  const handleUpload = (): void => {
    if (!file) {
      return;
    }
    setProgress(0);
    uploadMutation.mutate(
      { file, onUploadProgress: (percent) => setProgress(percent) },
      {
        onSuccess: (project) => navigate(`/projects/${project.id}`),
        onError: () => setProgress(null),
      },
    );
  };

  return (
    <PageWrapper>
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-2xl font-bold text-gray-900">New project</h1>

        <GlassCard className="bg-white/70">
          <div className="mb-6 flex gap-2 rounded-xl bg-gray-100 p-1">
            {TABS.map((entry) => (
              <motion.button
                key={entry.id}
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={() => setTab(entry.id)}
                className={cn(
                  'flex flex-1 items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                  tab === entry.id
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900',
                )}
              >
                {entry.label}
                {entry.id === 'url' && (
                  <span className="rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-purple-700">
                    Soon
                  </span>
                )}
              </motion.button>
            ))}
          </div>

          {tab === 'upload' ? (
            <div className="flex flex-col gap-4">
              <UploadDropzone
                file={file}
                onFile={setFile}
                onClear={() => {
                  setFile(null);
                  setProgress(null);
                }}
                progress={progress}
                isUploading={uploadMutation.isPending}
              />

              {uploadMutation.isError && (
                <p className="text-sm text-red-500" role="alert">
                  {uploadMutation.error.message}
                </p>
              )}

              <div className="flex justify-end">
                <GradientButton
                  type="button"
                  onClick={handleUpload}
                  disabled={!file || uploadMutation.isPending}
                  aria-busy={uploadMutation.isPending}
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Start processing'}
                </GradientButton>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-gray-300 bg-white/50 px-6 py-12 text-center">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-purple-100 text-purple-700">
                <Clock className="h-5 w-5" />
              </span>
              <p className="text-sm font-semibold text-gray-900">
                Importing from a YouTube or video link is coming soon
              </p>
              <p className="max-w-sm text-sm text-gray-500">
                For now, download the video and upload the file directly. We&rsquo;re
                working on reliable link import and will turn it on here when it&rsquo;s
                ready.
              </p>
              <button
                type="button"
                onClick={() => setTab('upload')}
                className="mt-1 text-sm font-medium text-purple-700 hover:text-purple-800"
              >
                Upload a file instead
              </button>
            </div>
          )}
        </GlassCard>
      </div>
    </PageWrapper>
  );
}
