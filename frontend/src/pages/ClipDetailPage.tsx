import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { motion } from 'framer-motion';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Download,
  Loader2,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { VerticalVideoPlayer } from '../components/clips/VerticalVideoPlayer';
import { CaptionEditor } from '../components/clips/CaptionEditor';
import { ReframeControl } from '../components/clips/ReframeControl';
import { BrollToggle } from '../components/clips/BrollToggle';
import { ClipScoreBadge } from '../components/clips/ClipScoreBadge';
import { ClipStatusPill } from '../components/clips/ClipCard';
import { formatSeconds } from '../services/clipService';
import type { ClipDetail, ClipStyle } from '../services/clipService';
import {
  useClip,
  useClipDownload,
  useDeleteClip,
  useRerenderClip,
  useUpdateClip,
} from '../hooks/useClips';

const secondaryButton =
  'inline-flex items-center gap-2 rounded-full border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 disabled:opacity-50';

// ---------------------------------------------------------------------------
// Title editor
// ---------------------------------------------------------------------------

function TitleEditor({
  clipId,
  title,
  disabled,
}: {
  clipId: number;
  title: string;
  disabled: boolean;
}) {
  const [value, setValue] = useState(title);
  const mutation = useUpdateClip(clipId);
  const trimmed = value.trim();
  const isDirty = trimmed.length > 0 && trimmed !== title;

  return (
    <div className="space-y-2">
      <AnimatedInput
        label="Title"
        type="text"
        value={value}
        disabled={disabled || mutation.isPending}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setValue(event.target.value)}
      />
      <div className="flex items-center gap-2">
        <motion.button
          type="button"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => mutation.mutate({ title: trimmed })}
          disabled={disabled || !isDirty || mutation.isPending}
          className={secondaryButton}
        >
          {mutation.isPending ? 'Saving...' : 'Save title'}
        </motion.button>
        {mutation.isError ? (
          <span className="text-xs text-red-500">{mutation.error.message}</span>
        ) : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail view
// ---------------------------------------------------------------------------

function ClipDetailView({ clipId }: { clipId: number }) {
  const navigate = useNavigate();
  const { data: clip, isLoading, isError, error } = useClip(clipId);
  const isReady = clip?.status === 'ready';
  const isRendering = clip?.status === 'queued' || clip?.status === 'rendering';

  const downloadHandle = useClipDownload(clipId, isReady);
  const rerender = useRerenderClip(clipId);
  const remove = useDeleteClip();

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-gray-400">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (isError || !clip) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        <AlertCircle className="h-4 w-4" />
        {error?.message ?? 'This clip could not be loaded.'}
      </div>
    );
  }

  const detail: ClipDetail = clip;
  const style = (detail.caption_style ?? {}) as ClipStyle;
  const previewUrl = detail.video_url ?? downloadHandle.url;

  const handleDelete = () => {
    if (!window.confirm('Delete this clip? This cannot be undone.')) {
      return;
    }
    remove.mutate(clipId, { onSuccess: () => navigate('/clips') });
  };

  return (
    <div className="mx-auto max-w-5xl">
      <Link
        to="/clips"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-purple-600"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to clips
      </Link>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">{detail.title}</h1>
        <ClipStatusPill status={detail.status} />
        <span className="text-sm text-gray-400">
          {formatSeconds(detail.duration_seconds)} &middot; {detail.aspect_ratio}
        </span>
      </div>

      {isRendering ? (
        <div className="mb-5 flex items-center gap-2 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700">
          <Loader2 className="h-4 w-4 animate-spin" />
          This clip is rendering. Editing and download are disabled until it is ready.
        </div>
      ) : null}
      {detail.status === 'failed' ? (
        <div className="mb-5 flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4" />
          Rendering failed. Try re-rendering the clip.
        </div>
      ) : null}

      <div className="grid gap-8 md:grid-cols-[280px_1fr]">
        <div className="space-y-4">
          <VerticalVideoPlayer
            src={isReady ? previewUrl : null}
            poster={detail.thumbnail_url}
            isLoading={isReady && downloadHandle.isFetching && !previewUrl}
          />

          <div className="flex flex-col gap-2">
            <GradientButton
              type="button"
              onClick={() => {
                void downloadHandle.download();
              }}
              disabled={!isReady || downloadHandle.isFetching}
              aria-busy={downloadHandle.isFetching}
            >
              <span className="inline-flex items-center gap-2">
                <Download className="h-4 w-4" />
                {downloadHandle.isFetching ? 'Preparing...' : 'Download MP4'}
              </span>
            </GradientButton>
            {downloadHandle.isError ? (
              <span className="text-xs text-red-500">
                Could not generate a download link.
              </span>
            ) : null}

            <motion.button
              type="button"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => rerender.mutate()}
              disabled={isRendering || rerender.isPending}
              className={secondaryButton}
            >
              <RefreshCw className="h-4 w-4" />
              {rerender.isPending ? 'Starting...' : 'Re-render'}
            </motion.button>
            {rerender.isError ? (
              <span className="text-xs text-red-500">{rerender.error.message}</span>
            ) : null}
            {rerender.isSuccess ? (
              <span className="text-xs text-green-600">Re-render queued.</span>
            ) : null}

            <motion.button
              type="button"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleDelete}
              disabled={remove.isPending}
              className="inline-flex items-center gap-2 rounded-full border border-red-200 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              {remove.isPending ? 'Deleting...' : 'Delete clip'}
            </motion.button>
            {remove.isError ? (
              <span className="text-xs text-red-500">{remove.error.message}</span>
            ) : null}
          </div>
        </div>

        <div className="space-y-6">
          <GlassCard className="bg-white/70">
            <div className="flex items-center gap-3">
              <ClipScoreBadge score={detail.score} />
              <span className="inline-flex items-center gap-1 text-xs font-medium text-purple-500">
                <Sparkles className="h-4 w-4" />
                AI interest score
              </span>
            </div>
            {detail.score_reason ? (
              <p className="mt-3 text-sm text-gray-600">{detail.score_reason}</p>
            ) : null}
          </GlassCard>

          <GlassCard className="bg-white/70">
            <TitleEditor clipId={clipId} title={detail.title} disabled={isRendering} />
          </GlassCard>

          <GlassCard className="bg-white/70">
            <CaptionEditor
              clipId={clipId}
              segments={detail.caption_segments ?? []}
              disabled={isRendering}
            />
          </GlassCard>

          <GlassCard className="bg-white/70">
            <ReframeControl clipId={clipId} captionStyle={style} disabled={isRendering} />
          </GlassCard>

          <GlassCard className="bg-white/70">
            <BrollToggle clipId={clipId} captionStyle={style} disabled={isRendering} />
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function ClipDetailPage() {
  const { id } = useParams<{ id: string }>();
  const clipId = id !== undefined ? Number(id) : Number.NaN;

  if (!Number.isFinite(clipId)) {
    return <Navigate to="/clips" replace />;
  }

  return (
    <PageWrapper>
      <ClipDetailView clipId={clipId} />
    </PageWrapper>
  );
}
