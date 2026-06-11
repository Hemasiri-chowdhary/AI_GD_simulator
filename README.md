# AI-GD-Pro 🎯

**AI-Powered Group Discussion Simulator for Placement Preparation**

A fully free, localhost-based AI Group Discussion simulator that provides realistic placement-level GD practice with multi-bot orchestration, smooth UI/UX, structured feedback, and stable backend performance.

## ✨ Features

- **5 AI Personas**: Moderator, Leader, Analyst, Opposer, and Supporter
- **Dynamic Turn-Taking**: Intelligent orchestration for natural discussion flow
- **Real-time Communication**: WebSocket-based low-latency interaction
- **Premium UI/UX**: Pastel gradient theme with smooth Framer Motion animations
- **Detailed Feedback**: Post-session performance analysis with actionable insights
- **100% Free & Local**: Runs entirely on localhost using Ollama

## 🛠️ Tech Stack

### Backend
- FastAPI (Python 3.10+)
- WebSockets
- SQLAlchemy + SQLite
- Ollama (Local LLM)

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion
- Zustand

## 📦 Prerequisites

1. **Python 3.10+**
2. **Node.js 18+**
3. **Ollama** - Install from [ollama.ai](https://ollama.ai)

## 🚀 Quick Start

### 1. Setup Ollama

```bash
# Install Ollama (Windows/Mac/Linux)
# Download from https://ollama.ai

# Pull the Llama 3 model
ollama pull llama3
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env

# Run the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### 4. Access the Application

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
gd_platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration settings
│   │   ├── database.py          # Database setup
│   │   ├── models/              # SQLAlchemy & Pydantic models
│   │   ├── routes/              # API & WebSocket routes
│   │   └── services/            # Business logic
│   │       ├── ollama_client.py # LLM wrapper
│   │       ├── orchestrator.py  # Turn-taking logic
│   │       ├── persona_manager.py
│   │       ├── topic_service.py
│   │       ├── feedback_service.py
│   │       └── session_manager.py
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── app/                 # Next.js App Router
    │   ├── components/          # React components
    │   ├── hooks/               # Custom hooks
    │   ├── store/               # Zustand state
    │   └── lib/                 # Utilities
    ├── package.json
    └── tailwind.config.js
```

## 🎮 How It Works

1. **Select Category**: Choose from Current Affairs, Technology, Abstract Topics, Business & Economy, or Ethics & Society
2. **Start Discussion**: The Moderator introduces a random topic from your selected category
3. **Participate**: Type your responses and engage with the AI bots
4. **Receive Feedback**: Get detailed performance analysis after the session

## 🤖 AI Personas

| Persona | Role |
|---------|------|
| **Moderator** | Introduces topic, manages flow, invites participants |
| **Arjun (Leader)** | Structures discussion, sets agenda |
| **Priya (Analyst)** | Provides data-backed arguments |
| **Rahul (Opposer)** | Challenges assumptions politely |
| **Sneha (Supporter)** | Builds consensus, supports ideas |

## ⚙️ Configuration

Edit `.env` in the backend folder:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
SESSION_DURATION_MINUTES=15
MAX_CONTEXT_MESSAGES=15
```

## 🎨 UI Theme

The application uses a premium pastel gradient theme:
- Lavender haze
- Peach sunset
- Mint glow
- Coral warmth
- Soft gold highlights

No blue, black, or white as primary colors.

## 📊 Feedback Metrics

- Confidence Score
- Clarity and Fluency
- Grammar and Vocabulary
- Argument Strength
- Participation Balance
- Leadership and Teamwork

## 🔧 Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### WebSocket Connection Failed
- Ensure backend is running on port 8000
- Check CORS settings if using different ports

## 📝 License

MIT License - Feel free to use for personal and educational purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Built with ❤️ for placement aspirants
