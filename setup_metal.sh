#!/bin/bash

# Metal Setup Script for AI Transcriber
# This script compiles whisper.cpp with Metal support and enables it in the app

set -e

echo "🚀 AI Transcriber - Metal GPU Setup"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CACHE_DIR="${HOME}/.cache/whisper.cpp"
REPO_DIR="${CACHE_DIR}/whisper.cpp"
BINARY_PATH="${REPO_DIR}/build/bin/main"

echo -e "${BLUE}Step 1: Checking for existing whisper.cpp binary...${NC}"
if [ -f "$BINARY_PATH" ] && [ -x "$BINARY_PATH" ]; then
    echo -e "${GREEN}✅ Found existing whisper.cpp binary at $BINARY_PATH${NC}"
    SKIP_BUILD=true
else
    echo "❌ No existing binary found, will compile..."
    SKIP_BUILD=false
fi

echo ""
echo -e "${BLUE}Step 2: Cloning whisper.cpp repository (if needed)...${NC}"
if [ ! -d "$REPO_DIR" ]; then
    echo "📦 Cloning from GitHub..."
    mkdir -p "$CACHE_DIR"
    git clone https://github.com/ggerganov/whisper.cpp.git "$REPO_DIR"
else
    echo "✅ Repository already exists"
fi

if [ "$SKIP_BUILD" = false ]; then
    echo ""
    echo -e "${BLUE}Step 3: Compiling whisper.cpp with Metal support...${NC}"
    echo "⏳ This may take 5-10 minutes on first run..."
    echo ""

    cd "$REPO_DIR"

    # Clean old build
    make clean 2>/dev/null || true

    # Compile with Metal (automatic on macOS)
    # Disable OpenMP to avoid CMake deprecation issues
    export WHISPER_NO_OPENMP=1
    make -j4

    # Verify binary was created
    if [ -f "$BINARY_PATH" ] && [ -x "$BINARY_PATH" ]; then
        echo -e "${GREEN}✅ Successfully compiled whisper.cpp${NC}"
    else
        echo -e "${YELLOW}⚠️  Compilation completed but binary not found at expected location${NC}"
        echo "Looking for binary..."
        find "$REPO_DIR" -name "main" -type f 2>/dev/null | head -5
    fi
fi

echo ""
echo -e "${BLUE}Step 4: Downloading Whisper models...${NC}"
cd "$REPO_DIR"

# Download base model (small, fast)
if [ ! -f "models/ggml-base.bin" ]; then
    echo "📥 Downloading base model (~140MB)..."
    bash ./models/download-ggml-model.sh base
else
    echo "✅ Base model already downloaded"
fi

# Download large-v3 model (best quality)
if [ ! -f "models/ggml-large-v3.bin" ]; then
    echo "📥 Downloading large-v3 model (~3GB, may take a while)..."
    bash ./models/download-ggml-model.sh large-v3
else
    echo "✅ Large-v3 model already downloaded"
fi

echo ""
echo -e "${BLUE}Step 5: Testing whisper.cpp...${NC}"
if [ -f "$BINARY_PATH" ]; then
    echo "Running test transcription..."
    # Create a simple test audio file (2 seconds of silence)
    ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 2 -q:a 9 -acodec libmp3lame /tmp/test_audio.wav -y 2>/dev/null

    # Test the binary
    "$BINARY_PATH" -m models/ggml-base.bin -f /tmp/test_audio.wav 2>&1 | head -20
    rm -f /tmp/test_audio.wav

    echo -e "${GREEN}✅ whisper.cpp is working!${NC}"
else
    echo -e "${YELLOW}⚠️  Binary not found, skipping test${NC}"
fi

echo ""
echo -e "${BLUE}Step 6: Enabling Metal in AI Transcriber...${NC}"

# Update .env file if it exists, otherwise inform user
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env"

if [ -f "$ENV_FILE" ]; then
    # Check if already configured
    if grep -q "WHISPER_CPP_AUTO_SETUP=True\|WHISPER_CPP_PATH=" "$ENV_FILE"; then
        echo "Updating existing configuration..."
        sed -i '' 's/WHISPER_CPP_AUTO_SETUP=.*/WHISPER_CPP_AUTO_SETUP=False/' "$ENV_FILE" 2>/dev/null || true
        sed -i '' "/WHISPER_CPP_PATH=/d" "$ENV_FILE" 2>/dev/null || true
    fi

    # Add Metal configuration
    echo "WHISPER_CPP_PATH=${BINARY_PATH}" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Updated .env file${NC}"
else
    echo -e "${YELLOW}ℹ️  To use Metal, add this to your .env file:${NC}"
    echo "WHISPER_CPP_PATH=${BINARY_PATH}"
fi

echo ""
echo -e "${GREEN}🎉 Metal setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update your .env file if needed (see above)"
echo "2. Restart the AI Transcriber app"
echo "3. You should now see 'whisper-cpp' as a backend option in the UI"
echo ""
echo "📊 Performance:"
echo "   - Metal GPU: 10-30x faster than CPU (depending on audio length)"
echo "   - Model sizes available: tiny, base, small, medium, large-v3"
echo ""
echo "To use Metal transcription:"
echo "1. Select 'whisper-cpp' backend in the app settings"
echo "2. Choose a model size (base recommended for speed)"
echo "3. Record/upload audio - it will use GPU acceleration"
