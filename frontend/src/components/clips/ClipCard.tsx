import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Scissors } from 'lucide-react';
import type { ClipListItem, ClipStyle } from '../../services/clipService';
import { formatSeconds } from '../../services/clipService';
import type { ClipStatus } from '../../types';
import { cn } from '../../lib/utils';
import { ClipScoreBadge } from './ClipScoreBadge';

// ---------------------------------------------------------------------------
// Status pill (shared with the detail page)
// ---------------------------------------------------------------------------

const STATUS_META: Record<ClipStatus, { label: string; className: string }> = {
  queued: { label: 'Queued', className: 'bg-gray-100 text-gray-600' },
  rendering: { label: 'Rendering', className: 'bg-blue-100 text-blue-700' },
  ready: { label: 'Ready', className: 'bg-green-100 text-green-700' },
  failed: { label: 'Failed', className: 'bg-red-100 text-red-700' },
};

export function ClipStatusPill({ status }: { status: ClipStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        meta.className,
      )}
    >
      {meta.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

export function ClipCard({ clip }: { clip: ClipListItem }) {
  // caption_style is absent on the list payload and null until a clip is
  // styled - guard before reading it.
  const style = (clip.caption_style ?? {}) as ClipStyle;
  const thumbnailUrl = clip.thumbnail_url ?? undefined;

  return (
    <motion.div
      whileHover={{ x: 4 }}
      whileTap={{ scale: 0.995 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
    >
      <Link
        to={`/clips/${clip.id}`}
        className="flex gap-4 rounded-2xl border border-gray-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md"
      >
        <div className="relative h-24 w-[54px] shrink-0 overflow-hidden rounded-lg bg-gradient-to-br from-purple-100 to-pink-100">
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-purple-300">
              <Scissors className="h-5 w-5" />
            </div>
          )}
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center gap-2">
            <ClipScoreBadge score={clip.score} size="sm" />
            <ClipStatusPill status={clip.status} />
            <span className="ml-auto text-xs text-gray-400">
              {formatSeconds(clip.duration_seconds)}
            </span>
          </div>
          <h3 className="truncate text-sm font-semibold text-gray-900">{clip.title}</h3>
          {clip.score_reason ? (
            <p className="line-clamp-2 text-xs text-gray-500">{clip.score_reason}</p>
          ) : null}
          {typeof style.reframe_offset === 'number' ? (
            <span className="text-[11px] text-gray-400">Reframed</span>
          ) : null}
        </div>
      </Link>
    </motion.div>
  );
}
