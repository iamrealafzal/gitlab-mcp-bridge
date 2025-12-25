# Docker Setup for Ollama

This guide will help you set up Ollama using Docker.

## Prerequisites

### Install Docker Desktop

**For macOS:**
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop/
2. Install Docker Desktop
3. Start Docker Desktop application
4. Verify installation:
   ```bash
   docker --version
   docker-compose --version
   ```

**For Linux:**
```bash
# Update package list
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
# Log out and log back in for this to take effect
```

## Running Ollama with Docker

### Option 1: Using Docker Compose (Recommended)

1. **Start Ollama:**
   ```bash
   docker-compose up -d
   ```

2. **Check if it's running:**
   ```bash
   docker ps
   ```

3. **Pull a model:**
   ```bash
   docker exec -it ollama ollama pull qwen2.5-coder:7b
   ```
   Or any other model:
   ```bash
   docker exec -it ollama ollama pull llama2
   docker exec -it ollama ollama pull codellama
   ```

4. **Test Ollama:**
   ```bash
   docker exec -it ollama ollama run qwen2.5-coder:7b "Hello, how are you?"
   ```

5. **Stop Ollama:**
   ```bash
   docker-compose down
   ```

### Option 2: Using Docker Run

```bash
# Run Ollama container
docker run -d \
  -v ollama_data:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  --restart unless-stopped \
  ollama/ollama

# Pull a model
docker exec -it ollama ollama pull qwen2.5-coder:7b

# Test
docker exec -it ollama ollama run qwen2.5-coder:7b "Hello"
```

## Configure in Django Admin

Once Ollama is running:

1. Go to **Django Admin > MCP Bridge > LLM Providers**
2. Click **Add LLM Provider**
3. Fill in:
   - **Name**: Ollama Docker
   - **Provider Type**: Ollama (Local)
   - **Base URL**: `http://localhost:11434` (or `http://127.0.0.1:11434`)
   - **API Key**: Leave blank
4. Click **Save**

5. Go to **MCP Bridge > AI Models**
6. Click **Add AI Model**
7. Fill in:
   - **Provider**: Ollama Docker
   - **Model ID**: `qwen2.5-coder:7b` (or any model you pulled)
   - **Display Name**: Qwen2.5 Coder 7B
   - **Is Default**: Check if you want this as default
8. Click **Save**

## Available Models

Some recommended models for code analysis:

- `qwen2.5-coder:7b` - Good for code generation and debugging
- `codellama:7b` - Code-focused model
- `llama2:7b` - General purpose
- `mistral:7b` - Fast and efficient
- `deepseek-coder:6.7b` - Specialized for coding

Pull any model with:
```bash
docker exec -it ollama ollama pull <model-name>
```

## Troubleshooting

### Port Already in Use

If port 11434 is already in use:
```bash
# Check what's using the port
lsof -i :11434

# Or change the port in docker-compose.yml
# Change "11434:11434" to "11435:11434" and update Django config
```

### Container Not Starting

```bash
# Check logs
docker logs ollama

# Restart container
docker restart ollama
```

### Models Not Persisting

Models are stored in the Docker volume `ollama_data`. They will persist even if you stop/restart the container. To remove all models:
```bash
docker-compose down -v  # This removes the volume too
```

## GPU Support (Linux with NVIDIA GPU)

If you have an NVIDIA GPU and want to use it:

1. Install NVIDIA Container Toolkit:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

2. Uncomment the GPU section in `docker-compose.yml`

3. Restart the container:
```bash
docker-compose down
docker-compose up -d
```

## Integration with GitLab MCP Bridge

Once configured, you can use Ollama in your MCP commands:

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"generate_fix","arguments":{"log_file_path":"logs/mixed_errors.log","connection_name":"My Gitlab","repository_name":"embibe-treasure_test_app_api","model_name":"Qwen2.5 Coder 7B"}},"id":3}' | python manage.py run_mcp
```

The system will automatically use Ollama if:
- The repository has `force_ollama=True` (privacy mode)
- Or you specify an Ollama model name in the command

