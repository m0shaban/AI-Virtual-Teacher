import gradio as gr
import os
import time
from huggingface_hub import InferenceClient
import numpy as np
import soundfile as sf
import librosa
from transformers import pipeline
from gtts import gTTS
import tempfile
from typing import Optional, Tuple, List, Dict, Any

# Main configurations and models
HF_TOKEN = os.getenv("HF_TOKEN")

# Available LLM models for user selection
AVAILABLE_MODELS = {
    "Zephyr 7B": "HuggingFaceH4/zephyr-7b-beta",
    "Llama 2 7B Chat": "meta-llama/Llama-2-7b-chat-hf",
    "Mistral 7B Instruct": "mistralai/Mistral-7B-Instruct-v0.1",
    "CodeLlama 7B": "codellama/CodeLlama-7b-Python-hf",
    "Falcon 7B Instruct": "tiiuae/falcon-7b-instruct",
    "OpenChat 3.5": "openchat/openchat-3.5-1210"
}

# Default models
DEFAULT_LLM_MODEL = "HuggingFaceH4/zephyr-7b-beta"
ASR_MODEL = "openai/whisper-base"
TTS_MODEL = "facebook/mms-tts-ara"

class VirtualTeacher:
    def __init__(self, model_name: str = DEFAULT_LLM_MODEL):
        """Initialize the Virtual Teacher with specified model."""
        self.client = InferenceClient(model_name, token=HF_TOKEN)
        self.model_name = model_name
        print(f"🎓 Virtual Teacher ready using model: {self.model_name}")

    def generate_response(self, message: str, teacher_type: str = "general", language: str = "english") -> str:
        """Generate educational response based on message and teacher type."""
        if language == "arabic":
            contexts = {
                "math": "أنت معلم رياضيات خبير تشرح المفاهيم بطريقة بسيطة ومفهومة",
                "science": "أنت معلم علوم شغوف تحب تبسيط المعلومات العلمية",
                "language": "أنت معلم لغة عربية متمكن تشرح القواعد والأدب بوضوح",
                "programming": "أنت مطور برمجيات خبير تشرح البرمجة بوضوح",
                "general": "أنت معلم متعدد التخصصات ودود ومساعد"
            }
            prompt = f"{contexts.get(teacher_type, contexts['general'])}\n\nالطالب يسأل: {message}\n\nأجب باللغة العربية بشكل تعليمي وواضح:"
        else:
            contexts = {
                "math": "You are an expert mathematics teacher who explains concepts in a simple and clear way",
                "science": "You are a passionate science teacher who loves to simplify scientific information",
                "language": "You are a skilled language teacher who explains grammar and literature clearly",
                "programming": "You are an expert software developer who explains programming concepts clearly",
                "general": "You are a friendly and helpful multi-disciplinary teacher"
            }
            prompt = f"{contexts.get(teacher_type, contexts['general'])}\n\nStudent asks: {message}\n\nRespond in English in an educational and clear manner:"
        try:
            response = self.client.text_generation(
                prompt,
                max_new_tokens=500,
                temperature=0.7,
                do_sample=True
            )
            return response.strip() if response else "Sorry, I couldn't generate a response."
        except Exception as e:
            return f"Error communicating with the model: {e}"

    def update_model(self, model_name: str):
        """Update the model being used."""
        try:
            self.client = InferenceClient(model_name, token=HF_TOKEN)
            self.model_name = model_name
            return f"✅ Model updated to: {model_name}"
        except Exception as e:
            return f"❌ Error updating model: {e}"

def initialize_pipelines():
    """Initialize and load audio models."""
    print("⏳ Initializing audio models (ASR & TTS)...")
    asr_pipeline = None
    tts_pipeline = None

    # Initialize Speech-to-Text model (ASR)
    try:
        asr_pipeline = pipeline("automatic-speech-recognition", model=ASR_MODEL, token=HF_TOKEN)
        print("👍 ASR Pipeline initialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing ASR model: {e}")

    # Initialize Text-to-Speech model (TTS)
    try:
        tts_pipeline = pipeline("text-to-speech", model=TTS_MODEL, token=HF_TOKEN)
        print("👍 TTS Pipeline initialized successfully.")
    except Exception as e:
        print(f"⚠️ Failed to initialize TTS model: {e}")
        print("ℹ️ Will fallback to gTTS.")

    return asr_pipeline, tts_pipeline

def create_app():
    """Build complete Gradio interface."""
    
    # Initialize models
    asr_pipe, tts_pipe = initialize_pipelines()
    teacher = VirtualTeacher()

    def update_model_handler(model_choice):
        """Handle model update."""
        if model_choice in AVAILABLE_MODELS:
            model_name = AVAILABLE_MODELS[model_choice]
            status = teacher.update_model(model_name)
            return status
        return "❌ Invalid model selection"

    def get_text_response(audio_input, text_input, teacher_type, language, history):
        """Process input and generate text response."""
        history = history or []
        user_message = ""

        if audio_input:
            try:
                y, sr = librosa.load(audio_input, sr=16000)
                if asr_pipe:
                    result = asr_pipe({"sampling_rate": sr, "raw": y})
                    if isinstance(result, dict) and "text" in result:
                        user_message = result["text"]
                    elif isinstance(result, str):
                        user_message = result
                    else:
                        user_message = str(result)
                else:
                    return history, "", "❌ Speech-to-text model not available", None
            except Exception as e:
                history.append(("(Audio error)", "Could not understand the audio."))
                return history, "", f"❌ Audio processing error: {e}", None
        elif text_input and text_input.strip():
            user_message = text_input.strip()
        else:
            return history, "", "Please ask your question first.", None

        # Generate response
        response_text = teacher.generate_response(user_message, teacher_type, language)
        history.append((user_message, response_text))
        
        return history, response_text, "✅ Text response generated", None

    def generate_audio_from_text(response_text, language):
        """Convert text to speech."""
        if not response_text:
            return "Please generate a text response first.", None

        try:
            if tts_pipe and language == "arabic":
                output = tts_pipe(response_text)
                if isinstance(output, dict) and "audio" in output and "sampling_rate" in output:
                    output_audio_path = tempfile.mktemp(suffix=".wav")
                    sf.write(output_audio_path, output["audio"], output["sampling_rate"])
                    return "✅ Audio generated successfully!", output_audio_path
                else:
                    raise Exception("Invalid TTS output format")
            else:
                # Use gTTS as fallback
                lang_code = 'ar' if language == "arabic" else 'en'
                tts = gTTS(text=response_text, lang=lang_code, slow=False)
                output_audio_path = tempfile.mktemp(suffix=".mp3")
                tts.save(output_audio_path)
                return "✅ Audio generated successfully!", output_audio_path

        except Exception as e:
            return f"❌ Audio generation failed: {e}", None

    # Custom CSS for better UI/UX
    custom_css = """
    .gradio-container { 
        font-family: 'Inter', sans-serif; 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    .main-header {
        text-align: center; 
        padding: 30px; 
        background: rgba(255, 255, 255, 0.1); 
        border-radius: 20px; 
        margin-bottom: 30px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .control-panel {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .chat-container {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .gr-button {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .gr-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .footer-info {
        text-align: center;
        margin-top: 30px;
        padding: 20px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    """

    # Design interface
    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="purple",
            neutral_hue="gray"
        ),
        css=custom_css,
        title="🎓 AI Virtual Teacher - By Mohamed Shaban"
    ) as app:
        
        # Header
        gr.HTML("""
        <div class="main-header">
            <h1 style="color: white; margin: 0; font-size: 3em; font-weight: 700;">
                🎓 AI Virtual Teacher
            </h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0; font-size: 1.2em;">
                Your Intelligent Educational Assistant - Multilingual & Multi-Model
            </p>
            <p style="color: rgba(255,255,255,0.7); margin: 5px 0;">
                Powered by Hugging Face Transformers
            </p>
        </div>
        """)

        with gr.Row():
            # Main chat area
            with gr.Column(scale=2):
                with gr.Group(elem_classes="chat-container"):
                    chatbot = gr.Chatbot(
                        label="💬 Conversation", 
                        height=500, 
                        avatar_images=("👨‍🎓", "🤖"),
                        bubble_full_width=False,
                        show_copy_button=True
                    )
                    
                    status_display = gr.Textbox(
                        label="📊 Status", 
                        interactive=False,
                        value="Welcome! Ask your question via voice or text"
                    )
                    
                    response_audio = gr.Audio(
                        label="🔊 Listen to Teacher's Response", 
                        interactive=False
                    )

            # Control panel
            with gr.Column(scale=1):
                with gr.Group(elem_classes="control-panel"):
                    gr.Markdown("### 🎛️ Control Panel")
                    
                    # Model selection
                    model_selector = gr.Dropdown(
                        choices=list(AVAILABLE_MODELS.keys()),
                        value="Zephyr 7B",
                        label="🤖 Select AI Model",
                        info="Choose the AI model for responses"
                    )
                    
                    # Language selection
                    language_selector = gr.Radio(
                        choices=[("English", "english"), ("العربية", "arabic")],
                        value="english",
                        label="🌐 Response Language"
                    )
                    
                    # Teacher type selection
                    teacher_type = gr.Dropdown(
                        choices=[
                            ("General 📚", "general"), 
                            ("Mathematics 🔢", "math"), 
                            ("Science 🔬", "science"), 
                            ("Programming 💻", "programming"),
                            ("Language 📖", "language")
                        ],
                        value="general", 
                        label="👨‍🏫 Teacher Specialization"
                    )
                    
                    gr.Markdown("### 🎤 Ask Your Question")
                    
                    audio_input = gr.Audio(
                        sources=["microphone"], 
                        type="filepath", 
                        label="🎤 Record your question"
                    )
                    
                    msg_text = gr.Textbox(
                        label="✍️ Or type your question here", 
                        lines=4,
                        placeholder="Example: Explain Newton's first law..."
                    )
                    
                    with gr.Row():
                        send_btn = gr.Button("📤 Send", variant="primary", scale=2)
                        clear_btn = gr.Button("🗑️ Clear", variant="secondary", scale=1)

        # Footer with credits
        gr.HTML("""
        <div class="footer-info">
            <h3 style="color: white; margin: 0;">👨‍💻 Created by Mohamed Shaban</h3>
            <p style="color: rgba(255,255,255,0.8); margin: 10px 0;">
                📧 <a href="mailto:eng.mohamed0shaban@gmail.com" style="color: #4CAF50;">eng.mohamed0shaban@gmail.com</a>
            </p>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0;">
                🔗 <a href="https://github.com/m0shaban" target="_blank" style="color: #4CAF50;">GitHub: @m0shaban</a>
            </p>
            <p style="color: rgba(255,255,255,0.6); margin: 5px 0; font-size: 0.9em;">
                Built with ❤️ using Gradio & Hugging Face
            </p>
        </div>
        """)

        # Hidden variable to store latest response
        latest_response = gr.Textbox(visible=False)

        # Event handlers
        model_selector.change(
            fn=update_model_handler,
            inputs=[model_selector],
            outputs=[status_display]
        )

        send_btn.click(
            fn=get_text_response,
            inputs=[audio_input, msg_text, teacher_type, language_selector, chatbot],
            outputs=[chatbot, latest_response, status_display, response_audio]
        ).then(
            fn=generate_audio_from_text,
            inputs=[latest_response, language_selector],
            outputs=[status_display, response_audio]
        )

        clear_btn.click(
            lambda: ([], "", "Conversation cleared. Start a new conversation!", None, ""),
            outputs=[chatbot, latest_response, status_display, response_audio, msg_text]
        )

        # Auto-example on load
        app.load(
            lambda: "Welcome! I'm your AI educational assistant. You can ask me about any educational topic in English or Arabic.",
            outputs=[status_display]
        )

    return app

if __name__ == "__main__":
    app = create_app()
    app.launch(
        share=True,
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False
    )
