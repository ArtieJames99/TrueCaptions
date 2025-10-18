# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil

# Try to ensure stdout/stderr use UTF-8 where possible to avoid UnicodeEncodeError on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# === Configuration ===
import pathlib

# support running from a frozen bundle (PyInstaller)
if getattr(sys, 'frozen', False):
    # when frozen, resources are unpacked to sys._MEIPASS
    BASE_DIR = pathlib.Path(sys._MEIPASS)
else:
    BASE_DIR = pathlib.Path(__file__).resolve().parent

SCRIPT_DIR = str(BASE_DIR)
FFMPEG_EXE = os.path.join(SCRIPT_DIR, "ffmpeg.exe")
FFMPEG_DIR = os.path.dirname(FFMPEG_EXE)
# allow overriding output dir via env, otherwise use a transcriptions folder next to the script
TRANSCRIPTIONS_DIR = os.environ.get('AUTOCAPTIONS_OUTDIR', str(pathlib.Path(SCRIPT_DIR) / 'transcriptions'))

# === Step 1: Verify ffmpeg exists ===
if not os.path.isfile(FFMPEG_EXE):
    # if ffmpeg not bundled, rely on PATH ffmpeg if available
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        FFMPEG_EXE = "ffmpeg"
        FFMPEG_DIR = os.path.dirname(shutil.which(FFMPEG_EXE) or "")
    except Exception:
        raise RuntimeError(f"ffmpeg.exe not found at {FFMPEG_EXE} and no ffmpeg on PATH")

os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ["PATH"]

# === Step 2: Import Whisper ===
try:
    import whisper
except ModuleNotFoundError:
    raise ModuleNotFoundError("Whisper is not installed in this Python environment.")

# === Step 3: Helper function to wrap text for line mode ===
def wrap_text_line_mode(text, max_chars=15):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + (1 if current_line else 0) + len(word) <= max_chars:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def split_words_into_lines(words, max_chars=20):
    """Group whisper word-timestamp dicts into lines of ~max_chars and return
    a list of dicts with text/start/end for each line. If words is empty,
    return an empty list.
    """
    if not words:
        return []

    lines = []
    current_words = []
    current_len = 0

    def flush_current():
        nonlocal current_words, current_len
        if not current_words:
            return
        text = " ".join(w.get("word", "").strip() for w in current_words).strip()
        start = current_words[0].get("start")
        end = current_words[-1].get("end")
        lines.append({"text": text, "start": start, "end": end})
        current_words = []
        current_len = 0

    for w in words:
        word_text = w.get("word", "").strip()
        # treat empty tokens as skipped
        if not word_text:
            continue
        add_len = len(word_text) + (1 if current_len else 0)
        if current_len + add_len <= max_chars:
            current_words.append(w)
            current_len += add_len
        else:
            flush_current()
            current_words.append(w)
            current_len = len(word_text)

    flush_current()
    return lines

# === Step 4: Save SRT ===
def save_srt(result, output_dir, mp4_file, line_mode=False, max_chars=20):
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(mp4_file))[0]
    srt_path = os.path.join(output_dir, base_name + ".srt")

    lines = []
    index = 1

    # compute total number of captions that will be emitted so GUI can report progress
    total_captions = 0
    if line_mode:
        for segment in result.get("segments", []):
            words = segment.get("words") or []
            word_lines = split_words_into_lines(words, max_chars=max_chars)
            if word_lines:
                total_captions += len(word_lines)
            else:
                text = segment.get("text", "").strip()
                text_lines = wrap_text_line_mode(text, max_chars=max_chars)
                total_captions += max(1, len(text_lines))
    else:
        total_captions = len(result.get("segments", []))

    # padding (in seconds) applied to caption end times to avoid cutting words early
    padding = float(os.environ.get('AUTOCAPTIONS_PADDING', '0.08'))

    def format_time(seconds):
        # guard against None
        if seconds is None:
            seconds = 0.0
        # round to nearest millisecond to avoid truncation that can cut off audio
        total_ms = int(round(seconds * 1000))
        ms = total_ms % 1000
        total_seconds = total_ms // 1000
        h = int(total_seconds // 3600)
        m = int((total_seconds % 3600) // 60)
        s = int(total_seconds % 60)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    for segment in result["segments"]:
        seg_start = segment.get("start")
        seg_end = segment.get("end")
        text = segment.get("text", "").strip()

        if line_mode:
            # Prefer using word timestamps to assign times per small line
            words = segment.get("words") or []
            word_lines = split_words_into_lines(words, max_chars=max_chars)

            if word_lines:
                for wl in word_lines:
                    start = wl.get("start", seg_start)
                    end = wl.get("end", seg_end)
                    # apply small padding to end times so words aren't cut off early
                    if end is not None:
                        end = end + padding
                    # avoid producing an end earlier than start due to rounding
                    if start is not None and end is not None and end <= start:
                        end = start + 0.001
                    text_line = wl.get("text", "")
                    lines.append(f"{index}")
                    lines.append(f"{format_time(start)} --> {format_time(end)}")
                    lines.append(text_line)
                    lines.append("")
                    # emit progress so UI can parse it
                    try:
                        print(f"PROGRESS: {index}/{total_captions}", flush=True)
                    except Exception:
                        pass
                    index += 1
            else:
                # fallback: split raw text and evenly distribute times across lines
                text_lines = wrap_text_line_mode(text, max_chars=max_chars)
                n = max(1, len(text_lines))
                seg_dur = (seg_end - seg_start) if (seg_start is not None and seg_end is not None) else 0
                for idx, tline in enumerate(text_lines):
                    if seg_dur > 0:
                        start = seg_start + (seg_dur * idx / n)
                        end = seg_start + (seg_dur * (idx + 1) / n)
                        # pad fallback-distributed lines as well
                        if end is not None:
                            end = end + padding
                    else:
                        start = seg_start or 0
                        end = seg_end or start
                    lines.append(f"{index}")
                    lines.append(f"{format_time(start)} --> {format_time(end)}")
                    lines.append(tline)
                    lines.append("")
                    try:
                        print(f"PROGRESS: {index}/{total_captions}", flush=True)
                    except Exception:
                        pass
                    index += 1
        else:
            # normal mode: one caption per segment
            lines.append(f"{index}")
            lines.append(f"{format_time(seg_start)} --> {format_time(seg_end)}")
            lines.append(text)
            lines.append("")
            try:
                print(f"PROGRESS: {index}/{total_captions}", flush=True)
            except Exception:
                pass
            index += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"SRT file saved to: {srt_path}")
    return srt_path

# === Step 5: Transcribe MP4 ===
def mp4_to_srt(mp4_file, line_mode=False):
    import tempfile
    import shutil
    import wave
    import contextlib

    print(f"Transcribing {mp4_file} ... this may take a while")
    model_name = os.environ.get('AUTOCAPTIONS_MODEL', 'small')
    # allow CLI --model
    if '--model' in sys.argv:
        try:
            m_idx = sys.argv.index('--model')
            model_name = sys.argv[m_idx + 1]
        except Exception:
            pass

    # chunking config (seconds)
    chunk_seconds = int(os.environ.get('AUTOCAPTIONS_CHUNK_SECONDS', '30'))

    # decide whether to chunk: use ffmpeg to split into wav segments
    tmpdir = tempfile.mkdtemp(prefix='autocaptions_')
    try:
        segment_pattern = os.path.join(tmpdir, 'seg%05d.wav')
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-i', mp4_file,
            '-vn', '-ac', '1', '-ar', '16000',
            '-f', 'segment', '-segment_time', str(chunk_seconds),
            '-reset_timestamps', '1', segment_pattern
        ]
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        except Exception:
            # if splitting fails, fallback to single-file transcription
            model = whisper.load_model(model_name)
            result = model.transcribe(mp4_file, word_timestamps=True)
            max_chars = int(os.environ.get('AUTOCAPTIONS_MAXCHARS', '20'))
            out_dir = os.environ.get('AUTOCAPTIONS_OUTDIR', TRANSCRIPTIONS_DIR)
            return save_srt(result, out_dir, mp4_file, line_mode=line_mode, max_chars=max_chars)

        # collect segments
        seg_files = sorted([os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.startswith('seg') and f.endswith('.wav')])
        if len(seg_files) <= 1:
            # single chunk, transcribe normally
            model = whisper.load_model(model_name)
            result = model.transcribe(mp4_file, word_timestamps=True)
            max_chars = int(os.environ.get('AUTOCAPTIONS_MAXCHARS', '20'))
            out_dir = os.environ.get('AUTOCAPTIONS_OUTDIR', TRANSCRIPTIONS_DIR)
            return save_srt(result, out_dir, mp4_file, line_mode=line_mode, max_chars=max_chars)

        # multi-chunk: transcribe each and stitch results
        model = whisper.load_model(model_name)
        all_segments = []
        total_chunks = len(seg_files)
        elapsed_offsets = []
        # precompute durations to calculate offsets
        durations = []
        for f in seg_files:
            try:
                with contextlib.closing(wave.open(f, 'r')) as wf:
                    dur = wf.getnframes() / float(wf.getframerate())
            except Exception:
                dur = chunk_seconds
            durations.append(dur)

        cumulative = 0.0
        for i, f in enumerate(seg_files, start=1):
            # transcribe chunk
            chunk_result = model.transcribe(f, word_timestamps=True)
            # adjust timestamps by cumulative offset
            for seg in chunk_result.get('segments', []):
                seg['start'] = seg.get('start', 0.0) + cumulative
                seg['end'] = seg.get('end', 0.0) + cumulative
                # adjust words if present
                if 'words' in seg:
                    for w in seg['words']:
                        if 'start' in w:
                            w['start'] = w.get('start') + cumulative
                        if 'end' in w:
                            w['end'] = w.get('end') + cumulative
                all_segments.append(seg)

            # report chunk progress
            try:
                print(f"PROGRESS_CHUNK: {i}/{total_chunks}", flush=True)
            except Exception:
                pass

            cumulative += durations[i-1]

        stitched = {'segments': all_segments}
        max_chars = int(os.environ.get('AUTOCAPTIONS_MAXCHARS', '15'))
        out_dir = os.environ.get('AUTOCAPTIONS_OUTDIR', TRANSCRIPTIONS_DIR)
        return save_srt(stitched, out_dir, mp4_file, line_mode=line_mode, max_chars=max_chars)
    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

# === Step 6: Main ===
def main():
    if len(sys.argv) < 2:
        raise ValueError("Usage: python AutoCaptions.py <path_to_mp4> [--mode normal|line]")

    mp4_file = sys.argv[1]
    if not os.path.isfile(mp4_file):
        raise FileNotFoundError(f"File not found: {mp4_file}")

    # Default mode is normal
    line_mode = True
    # simple arg parsing for --mode and optional --max-chars
    if '--mode' in sys.argv:
        try:
            mode_idx = sys.argv.index('--mode')
            mode_val = sys.argv[mode_idx + 1].lower()
            if mode_val == 'line':
                line_mode = True
        except Exception:
            pass

    if '--max-chars' in sys.argv:
        try:
            max_idx = sys.argv.index('--max-chars')
            os.environ['AUTOCAPTIONS_MAXCHARS'] = str(int(sys.argv[max_idx + 1]))
        except Exception:
            pass

    mp4_to_srt(mp4_file, line_mode=line_mode)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Print the error and exit with non-zero code when running as script
        print(f"ERROR: {e}")
        sys.exit(1)
