import { Loader2 } from 'lucide-react';

interface VerticalVideoPlayerProps {
  src: string | null;
  poster?: string | null;
  isLoading?: boolean;
  /** Optional message shown when there is no playable source yet. */
  placeholder?: string;
}

/**
 * A 9:16 <video> rendered inside a phone-style frame. Falls back to a loading
 * spinner or a placeholder message when no source is available.
 */
export function VerticalVideoPlayer({
  src,
  poster,
  isLoading = false,
  placeholder = 'Preview will be available once rendering finishes.',
}: VerticalVideoPlayerProps) {
  return (
    <div className="mx-auto w-full max-w-[280px]">
      <div className="relative overflow-hidden rounded-[2.25rem] border-[10px] border-gray-900 bg-gray-900 shadow-2xl">
        <div className="aspect-[9/16] w-full bg-black">
          {isLoading ? (
            <div className="flex h-full w-full items-center justify-center text-gray-400">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : src ? (
            <video
              key={src}
              src={src}
              poster={poster ?? undefined}
              controls
              playsInline
              preload="metadata"
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center px-6 text-center text-xs text-gray-400">
              {placeholder}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
