import { useState } from 'react';
import { motion } from 'framer-motion';
import { Clapperboard } from 'lucide-react';
import { GradientButton } from '../ui/GradientButton';
import { useUpdateClip } from '../../hooks/useClips';
import type { ClipStyle } from '../../services/clipService';

interface BrollToggleProps {
  clipId: number;
  captionStyle: ClipStyle;
  disabled?: boolean;
}

/**
 * Turns automatic stock-footage B-roll on/off for a clip. Persisted inside
 * `caption_style.broll` (boolean) via PUT /clips/{id}; changing it queues a
 * re-render.
 */
export function BrollToggle({ clipId, captionStyle, disabled = false }: BrollToggleProps) {
  const current = captionStyle.broll ?? false;
  const [enabled, setEnabled] = useState<boolean>(current);
  const mutation = useUpdateClip(clipId);
  const dirty = enabled !== current;

  const save = () => {
    mutation.mutate({ caption_style: { ...captionStyle, broll: enabled } });
  };

  return (
    <div>
      <div className="flex items-center gap-2">
        <Clapperboard className="h-4 w-4 text-purple-500" />
        <h2 className="text-sm font-semibold text-gray-900">B-roll</h2>
      </div>
      <p className="mt-1 text-sm text-gray-600">
        Auto-insert relevant stock footage over a few moments of the clip.
      </p>

      <motion.button
        type="button"
        role="switch"
        aria-checked={enabled}
        disabled={disabled}
        whileTap={{ scale: 0.95 }}
        onClick={() => setEnabled((v) => !v)}
        className={`mt-3 flex h-7 w-12 rounded-full p-1 transition-colors disabled:opacity-50 ${
          enabled ? 'justify-end bg-purple-500' : 'justify-start bg-gray-300'
        }`}
      >
        <span className="h-5 w-5 rounded-full bg-white shadow" />
      </motion.button>

      {mutation.isError ? (
        <p className="mt-2 text-sm text-red-600">{mutation.error.message}</p>
      ) : null}

      <div className="mt-3">
        <GradientButton type="button" onClick={save} disabled={disabled || !dirty || mutation.isPending}>
          {mutation.isPending ? 'Saving...' : 'Apply & re-render'}
        </GradientButton>
      </div>
    </div>
  );
}
