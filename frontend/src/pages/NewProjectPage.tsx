import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { UploadDropzone } from '../components/projects/UploadDropzone';
import { UrlImportForm } from '../components/projects/UrlImportForm';
import { useCreateProjectFromUrl, useUploadProject } from '../hooks/useProjects';
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
  const urlMutation = useCreateProjectFromUrl();

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

  const handleUrl = (url: string): void => {
    urlMutation.mutate(url, {
      onSuccess: (project) => navigate(`/projects/${project.id}`),
    });
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
                  'flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                  tab === entry.id
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900',
                )}
              >
                {entry.label}
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
            <UrlImportForm
              onSubmit={handleUrl}
              isSubmitting={urlMutation.isPending}
              error={urlMutation.isError ? urlMutation.error.message : null}
            />
          )}
        </GlassCard>
      </div>
    </PageWrapper>
  );
}
