import { useEffect, useState } from 'react';
import type { ChangeEvent } from 'react';
import { motion } from 'framer-motion';
import { GradientButton } from '../ui/GradientButton';
import { clampOffset } from '../../services/clipService';
import type { ClipStyle } from '../../services/clipService';
import { useUpdateClip } from '../../hooks/useClips';

interface ReframeControlProps {
  clipId: number;
  captionStyle: ClipStyle;
  disabled?: boolean;
}

/**
 * Horizontal-offset slider that chooses which part of the original 16:9 frame
 * stays centred in the vertical 9:16 crop. Persisted inside caption_style
 * as `reframe_offset` (0..1) via PUT /clips/{id}.
 */
export function ReframeControl({ clipId, captionStyle, disabled = false }: ReframeControlProps) {
  const initial = clampOffset(captionStyle.reframe_offset ?? 0.5);
  const [offset, setOffset] = useState(initial);
  const mutation = useUpdateClip(clipId);

  useEffect(() => {
    setOffset(initial);
  }, [initial]);

  const isDirty = Math.abs(offset - initial) > 0.001;
  const percent = Math.round(offset * 100);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    setOffset(clampOffset(Number(event.target.value) / 100));
  };

  const handleSave = () => {
    mutation.mutate({ caption_style: { ...captionStyle, reframe_offset: offset } });
  };

  const handleReset = () => {
    setOffset(initial);
    mutation.reset();
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Reframe</h3>
        <span className="text-xs text-gray-400">{percent}%</span>
      </div>
      <p className="text-xs text-gray-500">
        Slide to choose which part of the original frame stays centred in the vertical crop.
      </p>

      <div className="relative h-14 overflow-hidden rounded-lg border border-gray-200 bg-gradient-to-r from-purple-100 via-pink-100 to-purple-100">
        <motion.div
          className="absolute bottom-1 top-1 w-10 -translate-x-1/2 rounded-md border-2 border-purple-600 bg-white/40"
          animate={{ left: `${percent}%` }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        />
      </div>

      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={percent}
        disabled={disabled || mutation.isPending}
        onChange={handleChange}
        aria-label="Horizontal crop centre"
        className="w-full accent-purple-600 disabled:opacity-50"
      />

      {mutation.isError ? (
        <p className="text-sm text-red-500" role="alert">
          {mutation.error.message}
        </p>
      ) : null}
      {mutation.isSuccess && !isDirty ? (
        <p className="text-sm text-green-600" role="status">
          Reframe saved.
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <GradientButton
          type="button"
          onClick={handleSave}
          disabled={disabled || !isDirty || mutation.isPending}
          aria-busy={mutation.isPending}
        >
          {mutation.isPending ? 'Saving...' : 'Save reframe'}
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
