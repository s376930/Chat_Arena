# Chat Arena

A real-time chat platform for scientific research where anonymous users are randomly paired, given shared conversation topics and individual hidden tasks.

## Features

- **Real-time WebSocket communication** for instant messaging
- **Random user pairing** with queue management
- **AI participants** - LLM-powered chat partners when no humans are available
- **Multi-provider support** - Anthropic Claude, OpenAI GPT, X Grok, and local Ollama models
- **Conversation topics** assigned to paired users
- **Hidden tasks** unique to each participant
- **Think/Speech input model** - users must write private thoughts before sending messages
- **Speech-to-text** using Web Speech API (with Whisper API fallback)
- **Dark/Light mode** toggle
- **Admin interface** for managing topics, tasks, and consent forms
- **Conversation storage** in HuggingFace chat format

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python run.py
```

### 3. Access the Application

- **Chat Interface**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `OPENAI_API_KEY` | OpenAI API key for Whisper & GPT | (optional) |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | (optional) |
| `XAI_API_KEY` | X.AI API key for Grok | (optional) |

### Data Files

Edit these JSON files in `server/data/`:

- **`topics_tasks.json`** - Conversation topics and hidden tasks
- **`consent.json`** - Consent form configuration
- **`llm_config.json`** - AI participant configuration
- **`personas.json`** - AI persona definitions

---

## AI Participants Configuration

Chat Arena can pair users with AI participants when no human partners are available. The AI system is designed to **fail gracefully** - if no LLM providers are configured or available, the application works normally with human-only pairing.

### Quick Start: Using Ollama (Local, Free)

The easiest way to enable AI participants is with **Ollama**, which runs locally on your machine:

#### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

#### 2. Pull the Default Model (gemma3)

```bash
ollama pull gemma3
```

#### 3. Start Ollama (if not auto-started)

```bash
ollama serve
```

That's it! The default configuration uses Ollama with gemma3. Start Chat Arena and AI participants will be available.

#### Alternative Ollama Models

You can use any model available in Ollama:

```bash
# List available models
ollama list

# Pull other models
ollama pull llama3.2
ollama pull mistral
ollama pull phi3
ollama pull codellama
```

To change the model, edit `server/data/llm_config.json`:

```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "model": "llama3.2",
      "base_url": "http://localhost:11434"
    }
  }
}
```

---

### Using Cloud API Providers

For better quality responses or when local resources are limited, you can use cloud APIs.

#### Option 1: Anthropic Claude

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)

2. Set the environment variable:
   ```bash
   export ANTHROPIC_API_KEY=your-api-key-here
   ```

3. Edit `server/data/llm_config.json`:
   ```json
   {
     "default_provider": "anthropic",
     "providers": {
       "anthropic": {
         "enabled": true,
         "model": "claude-sonnet-4-20250514",
         "api_key_env": "ANTHROPIC_API_KEY"
       },
       "ollama": {
         "enabled": false
       }
     }
   }
   ```

#### Option 2: OpenAI GPT

1. Get an API key from [platform.openai.com](https://platform.openai.com)

2. Set the environment variable:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

3. Edit `server/data/llm_config.json`:
   ```json
   {
     "default_provider": "openai",
     "providers": {
       "openai": {
         "enabled": true,
         "model": "gpt-4o",
         "api_key_env": "OPENAI_API_KEY"
       },
       "ollama": {
         "enabled": false
       }
     }
   }
   ```

#### Option 3: X Grok

1. Get an API key from [x.ai](https://x.ai)

2. Set the environment variable:
   ```bash
   export XAI_API_KEY=your-api-key-here
   ```

3. Edit `server/data/llm_config.json`:
   ```json
   {
     "default_provider": "grok",
     "providers": {
       "grok": {
         "enabled": true,
         "model": "grok-2",
         "api_key_env": "XAI_API_KEY",
         "base_url": "https://api.x.ai/v1"
       },
       "ollama": {
         "enabled": false
       }
     }
   }
   ```

---

### Full Configuration Reference

The complete `llm_config.json` structure:

```json
{
  "enabled": true,
  "default_provider": "ollama",
  "providers": {
    "anthropic": {
      "enabled": false,
      "model": "claude-sonnet-4-20250514",
      "api_key_env": "ANTHROPIC_API_KEY"
    },
    "openai": {
      "enabled": false,
      "model": "gpt-4o",
      "api_key_env": "OPENAI_API_KEY"
    },
    "grok": {
      "enabled": false,
      "model": "grok-2",
      "api_key_env": "XAI_API_KEY",
      "base_url": "https://api.x.ai/v1"
    },
    "ollama": {
      "enabled": true,
      "model": "gemma3",
      "base_url": "http://localhost:11434"
    }
  },
  "behavior": {
    "idle_timeout_seconds": 120,
    "idle_check_interval_seconds": 30,
    "response_delay_min_ms": 500,
    "response_delay_max_ms": 3000
  },
  "ai_participants": {
    "force_ai_on_odd_users": true,
    "max_ai_participants": 5
  },
  "pairing": {
    "delay_enabled": true,
    "reassign_delay_seconds": 10
  }
}
```

#### Configuration Options

| Section | Option | Description | Default |
|---------|--------|-------------|---------|
| **Root** | `enabled` | Enable/disable AI features globally | `true` |
| **Root** | `default_provider` | Which provider to use | `"ollama"` |
| **behavior** | `idle_timeout_seconds` | Seconds before AI re-engages idle partner | `120` |
| **behavior** | `response_delay_min_ms` | Minimum typing simulation delay | `500` |
| **behavior** | `response_delay_max_ms` | Maximum typing simulation delay | `3000` |
| **ai_participants** | `force_ai_on_odd_users` | Auto-pair lone users with AI | `true` |
| **ai_participants** | `max_ai_participants` | Maximum concurrent AI sessions | `5` |
| **pairing** | `delay_enabled` | Add delay after reassignment | `true` |
| **pairing** | `reassign_delay_seconds` | Seconds to wait before re-pairing | `10` |

---

### Disabling AI Participants

To run Chat Arena without AI participants (human-only mode):

```json
{
  "enabled": false
}
```

Or disable auto-pairing with AI while keeping AI available:

```json
{
  "enabled": true,
  "ai_participants": {
    "force_ai_on_odd_users": false
  }
}
```

---

### AI Personas

AI participants have distinct personalities defined in `server/data/personas.json`. Three default personas are included:

- **Alex** - Curious, warm, asks thoughtful follow-up questions
- **Sam** - Analytical, direct, breaks down complex topics
- **Jordan** - Empathetic, supportive, focuses on feelings

You can customize or add personas by editing the JSON file.

---

### Troubleshooting AI Features

| Issue | Solution |
|-------|----------|
| AI not available | Check if Ollama is running: `ollama list` |
| Model not found | Pull the model: `ollama pull gemma3` |
| API key errors | Verify environment variable is set correctly |
| Slow responses | Try a smaller model like `phi3` or `gemma3` |
| AI features disabled | Check `enabled: true` in `llm_config.json` |

Check the server logs for detailed error messages:
```bash
python run.py
# Look for "AI Manager initialized with providers" or warning messages
```

**Note:** If AI providers fail to initialize, the application continues to work normally with human-only pairing. No configuration is required if you don't want AI features.

## Project Structure

```
chat_arena/
├── server/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration settings
│   ├── models.py               # Pydantic models
│   ├── websocket_manager.py    # WebSocket connection manager
│   ├── pairing_service.py      # User pairing & queue logic
│   ├── storage_service.py      # Conversation storage
│   ├── llm/                    # AI participant system
│   │   ├── __init__.py
│   │   ├── config.py           # LLM configuration loader
│   │   ├── base.py             # Abstract provider class
│   │   ├── providers/          # LLM provider implementations
│   │   │   ├── anthropic.py    # Claude provider
│   │   │   ├── openai_provider.py  # GPT provider
│   │   │   ├── grok.py         # X Grok provider
│   │   │   └── ollama.py       # Local Ollama provider
│   │   ├── personas.py         # AI persona management
│   │   ├── memory.py           # Conversation memory
│   │   ├── context.py          # System prompt builder
│   │   ├── sentiment.py        # Sentiment analysis
│   │   ├── ai_participant.py   # AI participant controller
│   │   └── ai_manager.py       # AI participant manager
│   └── data/
│       ├── topics_tasks.json   # Editable topics & tasks
│       ├── consent.json        # Editable consent declaration
│       ├── llm_config.json     # AI configuration
│       ├── personas.json       # AI persona definitions
│       └── conversations/      # Stored conversations
│
├── static/
│   ├── index.html              # Main chat interface
│   ├── admin.html              # Admin page
│   ├── css/
│   │   ├── styles.css          # Main styles with dark mode
│   │   └── admin.css           # Admin page styles
│   └── js/
│       ├── app.js              # Main application logic
│       ├── websocket.js        # WebSocket client
│       ├── ui.js               # UI interactions
│       ├── speech.js           # Speech-to-text
│       └── admin.js            # Admin page logic
│
├── requirements.txt            # Python dependencies
├── run.py                      # Startup script
└── README.md
```

## How It Works

### User Flow

1. User accepts consent form
2. User enters the pairing queue
3. When two users are available, they are paired
4. Both receive the same conversation topic
5. Each receives a different hidden task
6. Users chat, writing "think" (private) then "speech" (sent)
7. Either user can request reassignment to a new partner
8. Conversations are saved in HuggingFace format

### Message Format

Messages are stored with private thoughts included:

```json
{
  "role": "user_abc123",
  "content": "<think>My strategy is to ask questions</think>What do you think about this topic?",
  "timestamp": "2026-01-19T10:00:00Z"
}
```

## Admin Features

The admin panel (`/admin`) allows researchers to:

- Add, edit, delete conversation topics
- Add, edit, delete hidden tasks
- Customize the consent form (title, content, checkboxes)
- Preview how consent appears to users

## API Endpoints

### WebSocket

- `ws://host:port/ws` - Main WebSocket endpoint for chat

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/consent` | Get consent form |
| POST | `/api/transcribe` | Transcribe audio (Whisper) |
| GET | `/api/admin/topics` | List topics |
| POST | `/api/admin/topics` | Create topic |
| PUT | `/api/admin/topics/{id}` | Update topic |
| DELETE | `/api/admin/topics/{id}` | Delete topic |
| GET | `/api/admin/tasks` | List tasks |
| POST | `/api/admin/tasks` | Create task |
| PUT | `/api/admin/tasks/{id}` | Update task |
| DELETE | `/api/admin/tasks/{id}` | Delete task |
| GET | `/api/admin/consent` | Get consent config |
| PUT | `/api/admin/consent` | Update consent config |

## Testing

1. Start the server: `python run.py`
2. Open two browser tabs to `http://localhost:8000`
3. Accept consent in both tabs
4. Verify both users are paired with a topic and different tasks
5. Test messaging between tabs
6. Verify the "think" field requirement (10+ characters)
7. Test reassignment
8. Check dark mode toggle
9. Verify conversations are saved in `server/data/conversations/`

## Deploying Online

This section provides step-by-step instructions for deploying Chat Arena to various web hosting platforms.

### Requirements for Hosting

Chat Arena requires a host that supports:
- **Python 3.9+** with pip
- **WebSocket connections** (critical for real-time chat)
- **Persistent file storage** (for conversation data)
- **Environment variables** for configuration

### Hosting Platform Comparison

| Platform | Free Tier | WebSocket Support | Persistent Storage | Ease of Use |
|----------|-----------|-------------------|-------------------|-------------|
| **Render** | Yes (with limits) | Full | Yes (with Disk) | Easy |
| **Railway** | $5 credit/month | Full | Yes | Very Easy |
| **Fly.io** | Yes (generous) | Full | Yes (Volumes) | Moderate |
| **Heroku** | No (from $5/mo) | Full | Yes (with add-ons) | Easy |
| **DigitalOcean** | No (from $5/mo) | Full | Yes | Moderate |

### Preparation Before Deployment

1. **Push your code to GitHub** (or GitLab/Bitbucket):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/chat-arena.git
   git push -u origin main
   ```

2. **Create a `Procfile`** in your project root (for some platforms):
   ```
   web: uvicorn server.main:app --host 0.0.0.0 --port $PORT
   ```

3. **Ensure `requirements.txt`** is up to date with all dependencies.

---

### Option 1: Deploy to Render (Recommended - Free Tier Available)

Render offers a generous free tier with native WebSocket support.

#### Step-by-Step:

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a new Web Service**:
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select the `chat-arena` repository

3. **Configure the service**:
   - **Name**: `chat-arena` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server.main:app --host 0.0.0.0 --port $PORT`

4. **Add environment variables** (Settings → Environment):
   - `OPENAI_API_KEY` - Your OpenAI key (optional, for Whisper)

5. **Add a Disk** (for persistent conversation storage):
   - Go to "Disks" in your service settings
   - Create a disk mounted at `/opt/render/project/src/server/data`
   - This ensures conversations persist across deployments

6. **Deploy**: Click "Create Web Service"

7. **Access your app** at `https://your-app-name.onrender.com`

> **Note**: Free tier services spin down after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

---

### Option 2: Deploy to Railway (Easy - $5 Free Credit/Month)

Railway offers simple deployment with a straightforward interface.

#### Step-by-Step:

1. **Create a Railway account** at [railway.app](https://railway.app)

2. **Create a new project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize and select your repository

3. **Configure settings**:
   - Railway auto-detects Python projects
   - Go to "Settings" → "Environment"
   - Add variables:
     - `PORT`: `8000`
     - `OPENAI_API_KEY`: Your key (optional)

4. **Set the start command** (if not auto-detected):
   - Go to Settings → Deploy
   - Set Start Command: `uvicorn server.main:app --host 0.0.0.0 --port $PORT`

5. **Add a volume** for persistent storage:
   - Click "New" → "Volume"
   - Mount path: `/app/server/data`

6. **Generate a domain**:
   - Go to Settings → Networking
   - Click "Generate Domain"

7. **Access your app** at the generated URL

---

### Option 3: Deploy to Fly.io (Free Tier with Volumes)

Fly.io offers excellent performance and WebSocket support.

#### Step-by-Step:

1. **Install the Fly CLI**:
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh

   # Windows
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. **Sign up and log in**:
   ```bash
   fly auth signup
   # or if you have an account:
   fly auth login
   ```

3. **Create a `fly.toml`** in your project root:
   ```toml
   app = "chat-arena"
   primary_region = "iad"

   [build]
     builder = "paketobuildpacks/builder:base"

   [env]
     PORT = "8080"

   [http_service]
     internal_port = 8080
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0

   [mounts]
     source = "chat_data"
     destination = "/app/server/data"
   ```

4. **Launch the app**:
   ```bash
   fly launch
   ```
   - Choose a unique app name
   - Select a region close to your users
   - Say "Yes" to creating a Postgres database if prompted (or skip)

5. **Create a volume** for persistent storage:
   ```bash
   fly volumes create chat_data --size 1 --region iad
   ```

6. **Set environment variables**:
   ```bash
   fly secrets set OPENAI_API_KEY=your-api-key-here
   ```

7. **Deploy**:
   ```bash
   fly deploy
   ```

8. **Access your app**:
   ```bash
   fly open
   ```
   Your app will be at `https://chat-arena.fly.dev`

---

### Option 4: Deploy to Heroku (Paid - from $5/month)

Heroku is well-documented and reliable.

#### Step-by-Step:

1. **Create a Heroku account** at [heroku.com](https://heroku.com)

2. **Install Heroku CLI**:
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku

   # Or download from heroku.com/cli
   ```

3. **Create a `Procfile`** in your project root:
   ```
   web: uvicorn server.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Create a `runtime.txt`** to specify Python version:
   ```
   python-3.11.0
   ```

5. **Deploy**:
   ```bash
   heroku login
   heroku create chat-arena-app
   git push heroku main
   ```

6. **Set environment variables**:
   ```bash
   heroku config:set OPENAI_API_KEY=your-api-key-here
   ```

7. **Access your app** at `https://chat-arena-app.herokuapp.com`

> **Note**: Heroku's ephemeral filesystem means conversation files are lost on each deploy. For production, consider using Heroku Postgres or an external database.

---

### Important Considerations

#### WebSocket Support
All recommended platforms support WebSockets. If using a different host, verify WebSocket support before deploying.

#### Persistent Storage
The app stores conversations as JSON files. On platforms with ephemeral filesystems:
- Use mounted volumes/disks (Render, Railway, Fly.io)
- Or modify the app to use a database (PostgreSQL, MongoDB)

#### HTTPS
Most platforms provide free SSL/HTTPS. WebSocket connections will automatically use `wss://` (secure WebSocket) when your site uses HTTPS.

#### Cold Starts
Free tier services often "sleep" after inactivity:
- First visitor after sleep experiences a delay (15-30 seconds)
- Subsequent requests are fast
- Consider a paid tier for production use

#### Custom Domains
All platforms support custom domains:
1. Add your domain in the platform's dashboard
2. Update your DNS records (usually CNAME to the platform's domain)
3. Wait for DNS propagation (up to 48 hours)

---

### Troubleshooting Deployment

| Issue | Solution |
|-------|----------|
| WebSocket connection fails | Ensure the platform supports WebSockets; check if using `wss://` for HTTPS |
| App crashes on start | Check logs; verify `requirements.txt` is complete |
| Conversations not saving | Verify persistent storage/volume is configured |
| 502 Bad Gateway | Check if the correct port is configured (`$PORT` env variable) |
| Module not found | Ensure all dependencies are in `requirements.txt` |

To view logs:
- **Render**: Dashboard → Logs
- **Railway**: Dashboard → Deployments → View Logs
- **Fly.io**: `fly logs`
- **Heroku**: `heroku logs --tail`

## License

MIT
