import { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, Loader2 } from 'lucide-react';
import { useProjectTranscriptQuery } from '../../hooks/useProjects';

interface TranscriptPanelProps {
  projectId: number;
  /** Whether transcription has finished and the transcript can be fetched. */
  available: boolean;
}

function formatTimestamp(totalSeconds: number): string {
  const seconds = Math.floor(totalSeconds % 60);
  const minutes = Math.floor(totalSeconds / 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/** Collapsible transcript viewer; fetches lazily the first time it is opened. */
export function TranscriptPanel({ projectId, available }: TranscriptPanelProps) {
  const [open, setOpen] = useState(false);
  const query = useProjectTranscriptQuery(projectId, open && available);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white/70">
      <motion.button
        type="button"
        whileTap={{ scale: 0.99 }}
        onClick={() => setOpen((value) => !value)}
        disabled={!available}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900 disabled:opacity-50"
      >
        <span>Transcript</span>
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="h-4 w-4" />
        </motion.span>
      </motion.button>

      {!available && (
        <p className="px-4 pb-3 text-xs text-gray-500">
          Available once transcription finishes.
        </p>
      )}

      {open && available && (
        <div className="max-h-96 overflow-y-auto border-t border-gray-100 px-4 py-3">
          {query.isLoading && (
            <div className="flex justify-center py-6 text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}

          {query.isError && (
            <p className="text-sm text-red-500">Could not load the transcript.</p>
          )}

          {query.isSuccess && query.data.segments.length === 0 && (
            <p className="text-sm text-gray-500">The transcript is empty.</p>
          )}

          {query.isSuccess && query.data.segments.length > 0 && (
            <ul className="flex flex-col gap-2">
              {query.data.segments.map((segment, index) => (
                <li key={`${segment.start}-${index}`} className="flex gap-3 text-sm">
                  <span className="shrink-0 font-mono text-xs text-purple-500">
                    {formatTimestamp(segment.start)}
                  </span>
                  <span className="text-gray-700">{segment.text}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
