# TrueCaptions
Automatic Closed Caption Generation for Video and Audio Content

# 🎬 Caption Generator

> A lightweight Python-based tool for generating **timed captions (SRT)** from MP4 video files, with flexible output styles for research, media production, and accessibility.

---

## 📖 Overview
The **Whisper Caption Generator** leverages [OpenAI Whisper](https://github.com/openai/whisper) to perform automatic speech recognition (ASR) on video files, producing high-quality captions with accurate timing.  

Unlike traditional caption workflows, this tool provides **fine-grained control** over caption formatting:

- One word at a time (karaoke-style)  
- Multiple words grouped per caption  
- Single-line or multi-line captions  
- Fully automated MP4 → SRT pipeline  

---

## 🎯 Objectives
- Automate caption generation for MP4s.  
- Provide configurable granularity: **word-level or line-level**.  
- Improve accessibility by ensuring only **one line at a time** is displayed when required.  
- Maintain portability: runs on **Windows, Linux, MacOS**.  

---

## 🛠️ Implementation

### Architecture
```mermaid
flowchart TD
    A[MP4 Input] --> B[Whisper ASR Engine]
    B --> C[Word/Line Segmentation]
    C --> D[Caption Formatter]
    D --> E[SRT Output]
````

### Key Features

- **Auto-transcription** with Whisper models (`tiny` → `large`).
    
- **Word timestamps** for precise syncing.
    
- **Flexible formatting**:
    
    - `--mode word` → one word per caption
        
    - `--mode line` → group `N` words
        
    - `--multiline` → allow wrapping vs. force single line
        
- **Auto-naming**: drag-and-drop `video.mp4` → generates `video.srt`
    

---

## 🚀 Usage

### Installation

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install openai-whisper srt
```

> [!warning]  
> On Windows systems with long path limitations, install into a **short-path environment** (e.g., `C:\pyenv` or `E:\pyenv`).

### Command Line

```bash
python mp4_to_srt.py video.mp4
```

**Examples**

```bash
# Line mode, 4 words per caption, one line only
python mp4_to_srt.py video.mp4 --mode line --max-words 4

# Word-by-word captions
python mp4_to_srt.py video.mp4 --mode word

# Allow multi-line, 6 words per caption
python mp4_to_srt.py video.mp4 --mode line --max-words 6 --multiline
```
---
## File Structure
```plaintext
VideoEditing
│   AutoCaptions.py
│   AutoCaptions_GUI.py
│   ffmpeg.exe
│
├───__pycache__
├───FFMPEG
└───transcriptions
```


---
## 💻 AutoCaptions.py
---
## 🔮 Future Work

- Export to **WebVTT** and **TXT** formats.
    
- GPU acceleration for faster transcription.
    
- Batch video processing.
    
- Advanced caption styling (timing adjustments, line wrapping).
    
- Improved error recovery and restart options.

---

## 📌 References

- [OpenAI Whisper](https://github.com/openai/whisper)
    
- PySide6
    
- [SubRip (SRT)](https://en.wikipedia.org/wiki/SubRip)
    
- PyInstaller
    

---

## 🏷️ Metadata

- **Author:** Elder AJ F Jex
    
- **Version:** 1.0
    
- **License:** 
    
- **Keywords:** Whisper, captions, GUI, PySide6, transcription, accessibility

