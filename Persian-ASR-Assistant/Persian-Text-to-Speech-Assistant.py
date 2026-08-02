# Persian-Text-to-Speech-Assistant
# ============================================================
# 🤖 Persian Text-to-Speech Assistant
# Input: typed text | Output: Persian voice
# Kaggle / Google Colab - single cell - CPU only (stable)
# ============================================================

# ---------- 1. Install libraries ----------
!pip install -q transformers torch soundfile numpy
!apt-get update -qq && apt-get install -y -qq ffmpeg

# ---------- 2. Import libraries ----------
import torch
import numpy as np
import soundfile as sf
import warnings
from transformers import AutoModelForCausalLM, AutoTokenizer, VitsModel, AutoTokenizer as VitsTokenizer
from IPython.display import HTML, display, Audio

warnings.filterwarnings('ignore')

# ---------- 3. Device setup -> force CPU ----------
DEVICE = "cpu"
print(f"🖥️  Device: {DEVICE}")
print("ℹ️  Running on CPU to avoid CUDA errors")

# ---------- 4. Load models ----------
print("\n⏳ Loading models (~1-2 minutes first time)...")

# LLM on CPU
LLM_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
llm_tokenizer = AutoTokenizer.from_pretrained(LLM_NAME)
llm_model = AutoModelForCausalLM.from_pretrained(
    LLM_NAME,
    torch_dtype=torch.float32,
).to(DEVICE)
print("  ✅ Language model (Qwen 1.5B) on CPU")

# Persian TTS Meta (MMS) on CPU
tts_model = VitsModel.from_pretrained("facebook/mms-tts-fas").to(DEVICE)
tts_tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-fas")
print("  ✅ Text-to-speech (MMS Persian)")
print("\n🚀 System ready!\n")

# ---------- 5. Core functions ----------
def generate_response(user_text):
    messages = [
        {"role": "system", "content": "شما یک دستیار هوشمند دوستانه هستید. پاسخ‌ها را کوتاه، مفید و کاملاً به زبان فارسی روان بنویسید."},
        {"role": "user", "content": user_text}
    ]
    prompt = llm_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = llm_tokenizer([prompt], return_tensors="pt").to(DEVICE)
    outputs = llm_model.generate(
        inputs.input_ids,
        max_new_tokens=250,
        do_sample=True,
        temperature=0.1,
        top_p=0.9,
        pad_token_id=llm_tokenizer.eos_token_id
    )
    response = llm_tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract only the assistant's reply
    if "assistant" in response:
        response = response.split("assistant")[-1].strip()
    return response

def text_to_speech(text, output_path="/kaggle/working/response.wav"):
    inputs = tts_tokenizer(text, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        waveform = tts_model(**inputs).waveform
    audio = waveform.cpu().numpy().squeeze()
    audio = audio / np.max(np.abs(audio))  # Normalize
    sf.write(output_path, audio, tts_model.config.sampling_rate)
    return output_path

# ---------- 6. Avatar UI ----------
display(HTML("""
<style>
@keyframes pulse {
    0% { transform: scale(1); box-shadow: 0 10px 30px rgba(67,233,123,0.3); }
    50% { transform: scale(1.12); box-shadow: 0 15px 40px rgba(67,233,123,0.5); }
    100% { transform: scale(1); box-shadow: 0 10px 30px rgba(67,233,123,0.3); }
}
.avatar-box {
    text-align: center; 
    padding: 30px; 
    font-family: 'Tahoma', Arial, sans-serif;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 25px;
    max-width: 500px;
    margin: 20px auto;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}
.avatar {
    width: 150px; 
    height: 150px; 
    border-radius: 50%; 
    margin: 0 auto;
    display: flex; 
    align-items: center; 
    justify-content: center;
    font-size: 70px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    box-shadow: 0 10px 30px rgba(102,126,234,0.4);
    transition: all 0.5s;
}
.avatar.speaking {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    animation: pulse 0.6s infinite;
}
.status-text {
    margin-top: 15px;
    font-size: 16px;
    color: white;
    padding: 8px 24px;
    border-radius: 20px;
    display: inline-block;
    background: #667eea;
    font-weight: bold;
    transition: all 0.3s;
}
.chat-bubble {
    background: white;
    border-radius: 12px;
    padding: 12px;
    margin: 10px 0;
    text-align: right;
    direction: rtl;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
</style>

<div class="avatar-box">
    <div id="avatar" class="avatar">🤖</div>
    <div id="status" class="status-text">✅ Ready</div>
    
    <div class="chat-bubble">
        <div style="color:#888; font-size:12px; margin-bottom:4px;">📝 Your text</div>
        <div id="user-text" style="color:#333; font-size:15px; min-height:20px;">-</div>
    </div>
    
    <div class="chat-bubble" style="border-right:4px solid #43e97b;">
        <div style="color:#888; font-size:12px; margin-bottom:4px;">💬 Assistant reply</div>
        <div id="bot-text" style="color:#764ba2; font-size:15px; font-weight:bold; min-height:20px;">-</div>
    </div>
</div>

<script>
window.updateUI = function(state, u, b) {
    var av = document.getElementById('avatar');
    var st = document.getElementById('status');
    if (state === 'speaking') {
        av.className = 'avatar speaking'; av.innerHTML = '🔊';
        st.style.background = '#43e97b'; st.innerText = '🔊 Speaking...';
    } else if (state === 'thinking') {
        av.className = 'avatar'; av.innerHTML = '🧠';
        st.style.background = '#00a8ff'; st.innerText = '🧠 Thinking...';
    } else {
        av.className = 'avatar'; av.innerHTML = '🤖';
        st.style.background = '#667eea'; st.innerText = '✅ Ready';
    }
    if (u) document.getElementById('user-text').innerText = u;
    if (b) document.getElementById('bot-text').innerText = b;
}
</script>
"""))

# ---------- 7. Chat loop ----------
print("=" * 55)
print("📝  Type your text and press Enter")
print("⛔  To exit: type 'exit' or press Ctrl+C")
print("=" * 55)

while True:
    try:
        print()
        user_input = input("📝 You: ")
        
        if user_input.strip().lower() in ["exit", "quit", "خروج"]:
            print("\n👋 Goodbye!")
            break
        
        if not user_input.strip():
            continue
            
        # Show thinking state
        display(HTML("<script>updateUI('thinking', " + 
                     repr(user_input)[1:] + ", '')</script>"))
        
        # Generate response
        bot_response = generate_response(user_input)
        print(f"🤖 Assistant: {bot_response}")
        
        # Show speaking state + play audio
        display(HTML("<script>updateUI('speaking', " + 
                     repr(user_input)[1:] + ", " + 
                     repr(bot_response)[1:] + ")</script>"))
        
        audio_path = text_to_speech(bot_response)
        display(Audio(audio_path, autoplay=True))
        
    except KeyboardInterrupt:
        print("\n\n👋 Stopped.")
        break
    except Exception as e:
        print(f"\n❌ Error: {e}")
