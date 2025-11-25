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

> [!warning]  
> This is best done on a virtual environment. Make sure python is installed on your system** (e.g., `C:\pyenv` or `E:\pyenv`).

**Build Virtual Environment**
```
Python -m venv .venv
```
**start .venv**
```
.venv/scripts/activate
```
**Install Depenencies**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install openai-whisper srt
pip install pyinstaller
```
Or

```
Pip install -r requirements.txt
```
**Download FFMPEG.exe**
[https://www.ffmpeg.org/download.html](https://www.gyan.dev/ffmpeg/builds)
Find the Full.zip and download. the ffmpeg.exe then can be moved to the folder ffmpeg under TrueCaptions. 
(ffmpeg.exe will usually be found under the bin folder.) 
Note: The zip file will look something like this: 
ffmpeg-release-full.7z

## File Structure
```plaintext
TrueCaptions
│   AutoCaptions.py
│   AutoCaptions_GUI.py
│   TrueCaptions.py
│
├───__pycache__
├───ffmpeg
|   |--- ffmpeg.exe
└───transcriptions
```
**Get EXE**
From file explorer, launch bulid.bat. Wait for install.
Your working application will be found in dist/truecaptions/
---

## 💻 TrueCaptions.exe
---

## 📌 References

- [OpenAI Whisper](https://github.com/openai/whisper)

- [FFMPEG](https://www.gyan.dev/ffmpeg/builds)
    
- PySide6
    
- [SubRip (SRT)](https://en.wikipedia.org/wiki/SubRip)
    
- PyInstaller
    

---

## 🏷️ Metadata

- **Author:** Elder AJ F Jex
    
- **Version:** 1.2
    
- **License:** 
    
- **Keywords:** Whisper, captions, GUI, PySide6, transcription, accessibility

