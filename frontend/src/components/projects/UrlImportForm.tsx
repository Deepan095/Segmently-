import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';

interface UrlImportFormProps {
  onSubmit: (url: string) => void;
  isSubmitting?: boolean;
  /** Server-side error message to surface below the field. */
  error?: string | null;
}

function isValidHttpUrl(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }
  return parsed.protocol === 'http:' || parsed.protocol === 'https:';
}

/** Single-field form for importing a project from a pasted video URL. */
export function UrlImportForm({ onSubmit, isSubmitting = false, error = null }: UrlImportFormProps) {
  const [url, setUrl] = useState('');
  const [fieldError, setFieldError] = useState<string | undefined>(undefined);

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmed = url.trim();
    if (!isValidHttpUrl(trimmed)) {
      setFieldError('Enter a valid http(s) URL.');
      return;
    }
    setFieldError(undefined);
    onSubmit(trimmed);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <AnimatedInput
        label="Video URL"
        type="url"
        inputMode="url"
        placeholder="https://www.youtube.com/watch?v=..."
        value={url}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setUrl(event.target.value)}
        error={fieldError}
      />
      <p className="text-xs text-gray-500">
        Paste a link to a YouTube or other publicly hosted video.
      </p>

      {error && (
        <p className="text-sm text-red-500" role="alert">
          {error}
        </p>
      )}

      <div className="flex justify-end">
        <GradientButton type="submit" disabled={isSubmitting} aria-busy={isSubmitting}>
          {isSubmitting ? 'Importing...' : 'Import video'}
        </GradientButton>
      </div>
    </form>
  );
}
