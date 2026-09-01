import { useRef, useState } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import { motion } from 'framer-motion';
import { FileVideo, UploadCloud, X } from 'lucide-react';
import { cn } from '../../lib/utils';

const MAX_SIZE_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB
const MAX_SIZE_LABEL = '2 GB';

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

interface UploadDropzoneProps {
  file: File | null;
  onFile: (file: File) => void;
  onClear: () => void;
  /** Integer 0-100 while uploading, or null when idle. */
  progress: number | null;
  isUploading: boolean;
}

/** Drag-and-drop / file-picker video upload with client-side validation. */
export function UploadDropzone({
  file,
  onFile,
  onClear,
  progress,
  isUploading,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCandidate = (candidate: File | undefined): void => {
    if (!candidate) {
      return;
    }
    if (!candidate.type.startsWith('video/')) {
      setError('Choose a video file (MP4, MOV, WebM, ...).');
      return;
    }
    if (candidate.size > MAX_SIZE_BYTES) {
      setError(`That file is ${formatBytes(candidate.size)}; the limit is ${MAX_SIZE_LABEL}.`);
      return;
    }
    setError(null);
    onFile(candidate);
  };

  const handleDrop = (event: DragEvent<HTMLButtonElement>): void => {
    event.preventDefault();
    setIsDragging(false);
    if (isUploading) {
      return;
    }
    handleCandidate(event.dataTransfer.files[0]);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>): void => {
    handleCandidate(event.target.files?.[0]);
    event.target.value = '';
  };

  const openPicker = (): void => {
    if (!isUploading) {
      inputRef.current?.click();
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={handleInputChange}
      />

      {file ? (
        <div className="rounded-2xl border-2 border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <FileVideo className="h-8 w-8 shrink-0 text-purple-500" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-900">{file.name}</p>
              <p className="text-xs text-gray-500">{formatBytes(file.size)}</p>
            </div>
            {!isUploading && (
              <motion.button
                type="button"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClear}
                aria-label="Remove file"
                className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </motion.button>
            )}
          </div>

          {progress !== null && (
            <div className="mt-3">
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <p className="mt-1 text-right text-xs text-gray-500">{progress}%</p>
            </div>
          )}
        </div>
      ) : (
        <motion.button
          type="button"
          onClick={openPicker}
          onDragOver={(event) => {
            event.preventDefault();
            if (!isUploading) {
              setIsDragging(true);
            }
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          whileHover={{ scale: isUploading ? 1 : 1.01 }}
          whileTap={{ scale: isUploading ? 1 : 0.99 }}
          disabled={isUploading}
          className={cn(
            'flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-10 text-center transition-colors',
            isDragging
              ? 'border-purple-500 bg-purple-50'
              : 'border-gray-300 bg-white hover:border-purple-400',
            isUploading && 'cursor-not-allowed opacity-60',
          )}
        >
          <UploadCloud className="h-10 w-10 text-purple-500" />
          <span className="text-sm font-medium text-gray-900">
            Drag a video here or click to browse
          </span>
          <span className="text-xs text-gray-500">
            MP4, MOV, WebM up to {MAX_SIZE_LABEL}
          </span>
        </motion.button>
      )}

      {error && (
        <p className="text-sm text-red-500" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
