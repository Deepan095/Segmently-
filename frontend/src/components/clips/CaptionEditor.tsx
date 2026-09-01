import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { GradientButton } from '../ui/GradientButton';
import { formatSeconds } from '../../services/clipService';
import { useUpdateClip } from '../../hooks/useClips';
import type { TranscriptSegment } from '../../types';

interface CaptionEditorProps {
  clipId: number;
  segments: TranscriptSegment[];
  /** Disable editing while the clip is queued/rendering. */
  disabled?: boolean;
}

const serialise = (segments: TranscriptSegment[]): string =>
  JSON.stringify(segments.map((segment) => segment.text));

/**
 * Edits the burned-in caption lines for a clip. Tracks a local dirty state and
 * persists changes through PUT /clips/{id} (caption_segments).
 */
export function CaptionEditor({ clipId, segments, disabled = false }: CaptionEditorProps) {
  const [draft, setDraft] = useState<TranscriptSegment[]>(segments);
  const mutation = useUpdateClip(clipId);

  useEffect(() => {
    setDraft(segments);
  }, [segments]);

  const isDirty = useMemo(
    () => serialise(draft) !== serialise(segments),
    [draft, segments],
  );

  const updateLine = (index: number, text: string) => {
    setDraft((previous) =>
      previous.map((segment, position) =>
        position === index ? { ...segment, text } : segment,
      ),
    );
  };

  const handleSave = () => {
    mutation.mutate({ caption_segments: draft });
  };

  const handleReset = () => {
    setDraft(segments);
    mutation.reset();
  };

  if (segments.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 p-4 text-sm text-gray-500">
        This clip has no caption segments to edit.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Captions</h3>
        <span className="text-xs text-gray-400">{draft.length} lines</span>
      </div>

      <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
        {draft.map((segment, index) => (
          <div key={index} className="rounded-xl border border-gray-200 bg-white p-2">
            <div className="mb-1 flex items-center gap-1 text-[11px] font-medium text-gray-400">
              <Clock className="h-3 w-3" />
              {formatSeconds(segment.start)} - {formatSeconds(segment.end)}
            </div>
            <textarea
              value={segment.text}
              rows={2}
              disabled={disabled || mutation.isPending}
              onChange={(event: ChangeEvent<HTMLTextAreaElement>) =>
                updateLine(index, event.target.value)
              }
              className="w-full resize-none rounded-lg border-2 border-gray-200 p-2 text-sm outline-none focus:border-purple-500 disabled:bg-gray-50"
            />
          </div>
        ))}
      </div>

      {mutation.isError ? (
        <p className="text-sm text-red-500" role="alert">
          {mutation.error.message}
        </p>
      ) : null}
      {mutation.isSuccess && !isDirty ? (
        <p className="text-sm text-green-600" role="status">
          Captions saved.
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <GradientButton
          type="button"
          onClick={handleSave}
          disabled={disabled || !isDirty || mutation.isPending}
          aria-busy={mutation.isPending}
        >
          {mutation.isPending ? 'Saving...' : 'Save captions'}
        </GradientButton>
        <motion.button
          type="button"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleReset}
          disabled={!isDirty || mutation.isPending}
          className="rounded-full border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 disabled:opacity-50"
        >
          Reset
        </motion.button>
      </div>
    </div>
  );
}
