import { motion } from 'framer-motion';
import { Link, Navigate } from 'react-router-dom';
import { ArrowRight, Film, Link2, Scissors, Sparkles, Type, Upload } from 'lucide-react';
import { MeshBackground } from '../components/layout/MeshBackground';
import { useAuth } from '../hooks/useAuth';

const MotionLink = motion(Link);

const STEPS = [
  {
    icon: Upload,
    title: 'Add a long video',
    body: 'Upload a file or paste a link — a podcast, webinar, talk or stream.',
  },
  {
    icon: Sparkles,
    title: 'AI finds the moments',
    body: 'It transcribes the audio and picks the self-contained ~1-minute segments that work as shorts.',
  },
  {
    icon: Scissors,
    title: 'Get vertical clips',
    body: '9:16, burned-in captions, ranked by an interest score. Preview, tweak, download.',
  },
];

const FEATURES = [
  {
    icon: Type,
    title: 'Captions that fit the frame',
    body: 'Word-timed captions in any script, wrapped and placed so nothing spills off the edges.',
  },
  {
    icon: Film,
    title: 'Optional B-roll',
    body: 'Auto-drops relevant stock footage over a few moments while your audio keeps playing.',
  },
  {
    icon: Link2,
    title: 'Import or upload',
    body: 'Direct video links and file uploads, cropped to vertical or fit over a blurred fill.',
  },
];

export function LandingPage() {
  const { user, isLoading } = useAuth();

  if (!isLoading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden text-gray-900">
      <MeshBackground />

      {/* nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-lg font-bold text-purple-700">Segmently</span>
        <nav className="flex items-center gap-2 text-sm">
          <MotionLink
            to="/login"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="rounded-full px-4 py-2 font-medium text-gray-600 hover:text-purple-700"
          >
            Log in
          </MotionLink>
          <MotionLink
            to="/register"
            whileHover={{ scale: 1.03, y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-2 font-semibold text-white shadow-sm"
          >
            Get started
          </MotionLink>
        </nav>
      </header>

      {/* hero */}
      <section className="mx-auto max-w-3xl px-6 pb-16 pt-10 text-center sm:pt-20">
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl"
        >
          Turn one long video into a week of shorts
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="mx-auto mt-5 max-w-xl text-lg text-gray-600"
        >
          Segmently watches your long-form videos, finds the moments that stand on their
          own, and cuts them into vertical, captioned ~1-minute clips ready for Shorts,
          Reels and TikTok. No editor required.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.16 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <MotionLink
            to="/register"
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-7 py-3 font-semibold text-white shadow-lg"
          >
            Start free <ArrowRight className="h-4 w-4" />
          </MotionLink>
          <MotionLink
            to="/login"
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="rounded-full border-2 border-gray-200 bg-white/70 px-7 py-3 font-semibold text-gray-700 backdrop-blur hover:border-gray-300"
          >
            Log in
          </MotionLink>
        </motion.div>
        <p className="mt-4 text-sm text-gray-500">
          For YouTubers, podcasters, streamers, educators and content teams.
        </p>
      </section>

      {/* how it works */}
      <section className="mx-auto max-w-5xl px-6 py-12">
        <h2 className="text-center text-sm font-semibold uppercase tracking-widest text-purple-600">
          How it works
        </h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="rounded-2xl border border-white/50 bg-white/60 p-6 shadow-sm backdrop-blur"
            >
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
                <step.icon className="h-5 w-5" />
              </div>
              <div className="text-xs font-semibold text-gray-400">Step {i + 1}</div>
              <h3 className="mt-1 text-base font-semibold text-gray-900">{step.title}</h3>
              <p className="mt-2 text-sm text-gray-600">{step.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* features */}
      <section className="mx-auto max-w-5xl px-6 py-12">
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl bg-white/50 p-6 backdrop-blur">
              <f.icon className="h-5 w-5 text-pink-500" />
              <h3 className="mt-3 text-base font-semibold text-gray-900">{f.title}</h3>
              <p className="mt-2 text-sm text-gray-600">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* closing CTA */}
      <section className="mx-auto max-w-3xl px-6 py-16 text-center">
        <h2 className="text-2xl font-bold text-gray-900 sm:text-3xl">
          Stop letting your best moments sit in a 2-hour video
        </h2>
        <MotionLink
          to="/register"
          whileHover={{ scale: 1.03, y: -2 }}
          whileTap={{ scale: 0.98 }}
          className="mt-6 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-7 py-3 font-semibold text-white shadow-lg"
        >
          Create your first clips <ArrowRight className="h-4 w-4" />
        </MotionLink>
      </section>

      <footer className="border-t border-white/40 py-8 text-center text-sm text-gray-500">
        Segmently · long videos in, short-form out
      </footer>
    </div>
  );
}
