# 🤖 Persian Text-to-Speech Assistant

A lightweight, fully browser-based Persian AI assistant that reads its responses aloud. 
Built for Google Colab and Kaggle Notebooks with zero local setup.

## ✨ Features
- 📝 Text Input (Persian/any language)
- 🧠 Local LLM (Qwen2.5-1.5B) — no API key
- 🔊 Persian TTS via Meta MMS
- 🤖 Animated Avatar UI
- 🚀 Single-cell execution
- 🖥️ CPU-first stable mode

## 🏗️ Architecture
User  Types → Qwen 1.5B LLM → Persian TTS → Audio + Avatar

## 🚀 Quick Start
Paste the single-cell script into Colab/Kaggle and run.

## 🧠 Models
| Component | Model | Size |
|-----------|-------|------|
| LLM | Qwen/Qwen2.5-1.5B-Instruct | 1.5B |
| TTS | facebook/mms-tts-fas | 145M |  b

## 🛠️ Troubleshooting
- CUDA error → Already fixed by forcing CPU
- attention_mask warning → Fixed explicitly
- Slow first run → Model download (~3GB)
