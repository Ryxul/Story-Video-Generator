import tkinter as tk
from gui import VideoGeneratorGUI
import sys
import os

def check_dependencies():
    """Check if required dependencies are installed and available"""
    try:
        # Check for Ollama service
        import ollama
        try:
            # Try to ping Ollama service
            ollama.chat(model='mistral', messages=[{'role': 'system', 'content': 'test'}])
        except ConnectionError:
            print("Warning: Ollama service is not running. Some features may be limited.")
            print("To use AI features, please start the Ollama service.")
        except Exception as e:
            if "model not found" in str(e).lower():
                print("Warning: Mistral model not found. To use AI features, run: ollama pull mistral")
    except ImportError:
        print("Warning: Ollama not installed. To use AI features, install with: pip install ollama")

    # Check for required folders and content
    if not os.path.exists("Background_Footage"):
        os.makedirs("Background_Footage")
        print("Created Background_Footage folder")
        print("Please add some video files (MP4, AVI, MOV, or MKV format) to the Background_Footage folder")
    else:
        # Check if folder has video files
        video_files = [f for f in os.listdir("Background_Footage") 
                      if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
        if not video_files:
            print("Warning: No video files found in Background_Footage folder")
            print("Please add some video files (MP4, AVI, MOV, or MKV format) to the Background_Footage folder")
    
    # Check for default background music
    if not os.path.exists("bg_music.wav"):
        print("Note: Default background music 'bg_music.wav' not found")

def main():
    """Initialize and run the application"""
    try:
        # Check dependencies
        check_dependencies()
        
        # Create main window
        root = tk.Tk()
        root.title("Video Generator")
        
        # Set minimum window size
        root.minsize(800, 800)
        
        # Create and initialize GUI
        app = VideoGeneratorGUI(root)
        
        # Start the application
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 