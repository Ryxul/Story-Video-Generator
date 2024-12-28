<div align="center">
  <h1>Story-Video-Generator</h1>
  
  [![Python](https://img.shields.io/badge/Python-3.8+-brightgreen)](https://www.python.org/)
  [![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

  🎥 Create professional videos from text or voiceovers with AI-powered enhancements
</div>

## Overview
Story-Video-Generator is a powerful desktop application that automates video content creation. Whether you start with text or a voiceover, it generates high quality short form videos with synchronized subtitles and background music.

## Key Features
- 🎙️ **Text-to-Speech Conversion**
  - Natural-sounding voices using Edge TTS
  - Multiple voice options
  - High-quality audio output

- 🤖 **AI Enhancement**
  - Story rephrasing with Mistral AI
  - Natural language optimization
  - Content engagement improvement

- 🎚️ **Professional Audio Mixing**
  - Real-time waveform visualization
  - Volume control and normalization
  - Smart deadspace removal (Experimental)
  - Live audio preview

- 📝 **Automated Subtitles**
  - Precise word-level timing
  - Animated text transitions


## Installation

### Prerequisites
- FFmpeg
- Ollama (optional, for AI features)

### Quick Start
```bash
# Clone repository
git clone https://github.com/Ryxul/Story-Video-Generator.git
cd Story-Video-Generator

# Create and activate virtual environment using Conda
conda create -n Story-Video-Generator python=3.9.19
conda activate Story-Video-Generator

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Additional Setup
For AI features:
```bash
# Install Ollama
# Visit: https://ollama.ai/download

# Download Mistral model
ollama pull mistral
```

## Usage

### Generate from Text
1. Enter or paste your story text
2. (Optional) Enhance with AI rephrasing
3. Generate voiceover audio
4. Fine-tune audio mix:
   - Adjust volumes
   - Remove deadspace
   - Preview results
5. Generate final video

### Generate from Voiceover
1. Import WAV format voiceover
2. Add background music
3. Adjust audio mix
4. Generate video with subtitles

## File Requirements

### Audio Files
- Format: WAV
- Sample rate: 16000 Hz required
- Channels: Mono or Stereo supported

### Video Files
- Formats: MP4 supported
- Resolution: 1920x1080 (Vertical/Portrait) only
- Orientation: Vertical/Portrait format only
- Frame rate: Any (output will be 60 FPS)

## Restrictions

### Important Format Requirements

1. **Audio Format**
   - Only WAV files are supported
   - Other formats (MP3, M4A, etc.) must be converted to WAV first

2. **Video Format**
   - Background footage must be in vertical/portrait format (1920x1080)
   - Horizontal videos will not work correctly
   - Output videos will always be vertical (1920x1080)

3. **Output**
   - Fixed resolution: 1920x1080 (Vertical)
   - Cannot output in horizontal format
   - Frame rate: 60 FPS (fixed)

> ⚠️ **Note**: Using incorrect video formats or orientations may result in errors or unexpected results. Please ensure all input files meet these requirements.

### Project Structure
```
Story-Video-Generator/
├── main.py              # Application entry point
├── gui.py              # Main GUI implementation
├── audio_widgets.py    # Audio processing interface
├── backend_processing.py # Core functionality
├── Background_Footage/  # Video clips folder
└── requirements.txt    # Dependencies
```

## Troubleshooting

### Common Issues
- **FFmpeg missing**: Install FFmpeg and ensure it's in system PATH
- **Ollama errors**: Check if service is running and model is downloaded
- **Audio issues**: Verify WAV file format and sample rate
- **Video errors**: Ensure clips are in supported formats

## Contributing
Contributions are welcome! Please feel free to submit pull requests.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
