# Docker Installation for macOS 12 (Monterey)

Your macOS version (12) is older than the latest Docker Desktop requirements. Here are your options:

## Option 1: Download Older Docker Desktop (Recommended)

1. **Download Docker Desktop 4.20 or earlier** which supports macOS 12:
   - Visit: https://docs.docker.com/desktop/release-notes/
   - Find a version that supports macOS 12
   - Or download directly: https://desktop.docker.com/mac/main/amd64/Docker.dmg

2. **Install Docker Desktop:**
   - Open the downloaded `.dmg` file
   - Drag Docker to Applications folder
   - Open Docker from Applications
   - Follow the setup wizard

3. **Verify installation:**
   ```bash
   docker --version
   docker-compose --version
   ```

## Option 2: Install Ollama Directly (Easier for macOS)

Since you're on macOS, you can install Ollama directly without Docker:

1. **Install Ollama:**
   ```bash
   brew install ollama
   ```

2. **Start Ollama:**
   ```bash
   ollama serve
   ```
   (This runs in the background)

3. **Pull a model:**
   ```bash
   ollama pull qwen2.5-coder:7b
   ```

4. **Configure in Django Admin:**
   - Base URL: `http://localhost:11434`
   - No Docker needed!

## Option 3: Use Docker via Colima (Alternative)

Colima is a Docker runtime for macOS that works on older versions:

```bash
# Install Colima
brew install colima docker docker-compose

# Start Colima
colima start

# Now Docker commands will work
docker --version
```

Then use the docker-compose.yml file as normal.

## Recommended: Use Ollama Directly

For macOS 12, I recommend **Option 2** (installing Ollama directly) as it's simpler and doesn't require Docker Desktop.

