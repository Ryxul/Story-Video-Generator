import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import asyncio
import os
from backend_processing import (process_story, create_master_track, 
                              create_video_compilation, process_segment_with_words)
import whisper
import threading
import random
import cv2
import shutil
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips, ImageSequenceClip
from audio_widgets import AudioPreviewWidget, MixerSettingsWindow
from pydub import AudioSegment
import numpy as np
import ollama

class VideoGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Story-Video-Generator")  # Updated title
        self.root.geometry("800x800")  # Made taller to accommodate new elements
        
        # Initialize variables first
        self.output_path_story = tk.StringVar(value="output.mp4")
        self.output_path_vo = tk.StringVar(value="output.mp4")
        self.bg_music_story = tk.StringVar(value="bg_music.wav")
        self.bg_music_vo = tk.StringVar(value="bg_music.wav")
        self.voiceover_path = tk.StringVar()
        self.video_folder_story = tk.StringVar(value="Background_Footage")
        self.video_folder_vo = tk.StringVar(value="Background_Footage")
        
        # Initialize volume settings
        self.vo_volume = 100
        self.bg_volume_story = 100
        self.bg_volume_vo = 100
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.story_tab = ttk.Frame(self.notebook)
        self.voiceover_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.story_tab, text='Generate from Story')
        self.notebook.add(self.voiceover_tab, text='Generate from Voiceover')
        
        # Setup both tabs
        self.setup_story_tab()
        self.setup_voiceover_tab()
        
        # Progress Section
        self.setup_progress_section()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var)
        self.status_bar.pack(side='bottom', fill='x', padx=10, pady=5)
        
    def setup_story_tab(self):
        # Story input frame
        story_frame = ttk.LabelFrame(self.story_tab, text="Story Input")
        story_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Story text area
        self.story_text = scrolledtext.ScrolledText(story_frame, height=10)
        self.story_text.pack(padx=10, pady=5, fill='both', expand=True)
        
        # Button frame for story controls
        story_controls = ttk.Frame(story_frame)
        story_controls.pack(fill='x', padx=10, pady=5)
        
        # Rephrase button
        ttk.Button(
            story_controls, 
            text="Rephrase with AI",
            command=self.rephrase_story
        ).pack(side='left', padx=5)
        
        # Clear button
        ttk.Button(
            story_controls,
            text="Clear Text",
            command=lambda: self.story_text.delete(1.0, tk.END)
        ).pack(side='left', padx=5)
        
        # Generate Voiceover button
        self.generate_vo_btn = ttk.Button(
            story_controls,
            text="Generate Voiceover",
            command=self.generate_story_voiceover
        )
        self.generate_vo_btn.pack(side='left', padx=5)
        
        # File inputs frame
        file_frame = ttk.LabelFrame(self.story_tab, text="File Selection")
        file_frame.pack(fill='x', padx=10, pady=5)
        
        # Background music selection with volume button
        bg_music_frame = ttk.Frame(file_frame)
        bg_music_frame.pack(side='top', fill='x', padx=10, pady=5)
        ttk.Label(bg_music_frame, text="Background Music:").pack(side='left', padx=10)
        ttk.Entry(bg_music_frame, textvariable=self.bg_music_story).pack(side='left', fill='x', expand=True)
        ttk.Button(bg_music_frame, text="Browse", 
                  command=lambda: self.browse_file(self.bg_music_story, [("WAV files", "*.wav")])).pack(side='right', padx=10)
        
        # Audio Mixer button (disabled initially)
        self.mixer_btn = ttk.Button(
            bg_music_frame, 
            text="Audio Mixer",
            command=self.open_mixer_settings,
            state='disabled'
        )
        self.mixer_btn.pack(side='right', padx=5)
        
        # Video folder selection
        folder_frame = ttk.Frame(file_frame)
        folder_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(folder_frame, text="Video Clips Folder:").pack(side='left', padx=10)
        ttk.Entry(folder_frame, textvariable=self.video_folder_story).pack(side='left', padx=10, fill='x', expand=True)
        ttk.Button(folder_frame, text="Browse", 
                  command=lambda: self.browse_folder(self.video_folder_story)).pack(side='right', padx=10)
        
        # Add output file selection
        output_frame = ttk.Frame(file_frame)
        output_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(output_frame, text="Output File:").pack(side='left', padx=10)
        ttk.Entry(output_frame, textvariable=self.output_path_story).pack(side='left', padx=10, fill='x', expand=True)
        ttk.Button(output_frame, text="Browse", 
                  command=lambda: self.browse_save_file(self.output_path_story)).pack(side='right', padx=10)
        
        # Generate Video button (disabled initially)
        self.generate_video_btn = ttk.Button(
            self.story_tab, 
            text="Generate Video",
            command=self.generate_from_story,
            state='disabled'
        )
        self.generate_video_btn.pack(padx=10, pady=20)
        
    def setup_voiceover_tab(self):
        # Voiceover file selection
        vo_frame = ttk.Frame(self.voiceover_tab)
        vo_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(vo_frame, text="Voiceover File:").pack(side='left', padx=10)
        ttk.Entry(vo_frame, textvariable=self.voiceover_path).pack(side='left', fill='x', expand=True)
        ttk.Button(vo_frame, text="Browse",
                  command=lambda: self.browse_file(self.voiceover_path, [("WAV files", "*.wav")])).pack(side='right', padx=10)
        
        # Background music selection
        bg_frame = ttk.Frame(self.voiceover_tab)
        bg_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(bg_frame, text="Background Music:").pack(side='left', padx=10)
        ttk.Entry(bg_frame, textvariable=self.bg_music_vo).pack(side='left', fill='x', expand=True)
        ttk.Button(bg_frame, text="Browse",
                  command=lambda: self.browse_file(self.bg_music_vo, [("WAV files", "*.wav")])).pack(side='right', padx=10)
        
        # Video folder selection
        folder_frame = ttk.Frame(self.voiceover_tab)
        folder_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(folder_frame, text="Video Clips Folder:").pack(side='left', padx=10)
        ttk.Entry(folder_frame, textvariable=self.video_folder_vo).pack(side='left', padx=10, fill='x', expand=True)
        ttk.Button(folder_frame, text="Browse", 
                  command=lambda: self.browse_folder(self.video_folder_vo)).pack(side='right', padx=10)
        
        # Add output file selection
        output_frame = ttk.Frame(self.voiceover_tab)
        output_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(output_frame, text="Output File:").pack(side='left', padx=10)
        ttk.Entry(output_frame, textvariable=self.output_path_vo).pack(side='left', padx=10, fill='x', expand=True)
        ttk.Button(output_frame, text="Browse", 
                  command=lambda: self.browse_save_file(self.output_path_vo)).pack(side='right', padx=10)
        
        # Generate button
        ttk.Button(self.voiceover_tab, text="Generate Video", 
                  command=self.generate_from_voiceover).pack(padx=10, pady=20)
        
        # Mixer button
        mixer_frame = ttk.Frame(self.voiceover_tab)
        mixer_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(mixer_frame, text="Audio Mixer",
                  command=self.open_mixer_settings).pack(side='right', padx=10)
        
    def browse_file(self, var, filetypes):
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)
            
    def browse_folder(self, var):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)
            
    def setup_progress_section(self):
        """Setup progress bar and output log section"""
        progress_frame = ttk.LabelFrame(self.root, text="Progress")
        progress_frame.pack(fill='x', padx=10, pady=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill='x', padx=10, pady=5)

        # Output log
        log_frame = ttk.LabelFrame(self.root, text="Output Log")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(
            log_frame, 
            height=10,
            wrap=tk.WORD
        )
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)

    def log_output(self, message):
        """Add message to output log"""
        self.output_text.insert(tk.END, f"{message}\n")
        self.output_text.see(tk.END)  # Scroll to bottom
        self.root.update()

    def update_progress(self, value, message=None):
        """Update progress bar and optionally log a message"""
        self.progress_var.set(value)
        if message:
            self.log_output(message)
        self.root.update()

    async def generate_from_story_async(self):
        try:
            if not hasattr(self, 'temp_vo_file'):
                messagebox.showerror("Error", "Please generate voiceover first")
                return
            
            self.progress_var.set(0)
            self.output_text.delete(1.0, tk.END)
            self.status_var.set("Generating video...")

            # Use the temporary voiceover file
            await self.generate_video(self.temp_vo_file, self.bg_music_story.get(), 
                                   self.video_folder_story.get())
            
            # Clean up temporary file
            if hasattr(self, 'temp_vo_file') and os.path.exists(self.temp_vo_file):
                if 'processed_vo_' in self.temp_vo_file:  # If it's a processed file
                    os.remove(self.temp_vo_file)
                delattr(self, 'temp_vo_file')
            
            self.update_progress(100, "Video generation complete!")
            messagebox.showinfo("Success", "Video generated successfully!")
            self.status_var.set("Ready")
            
        except Exception as e:
            self.log_output(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error occurred")

    def generate_from_story(self):
        asyncio.run(self.generate_from_story_async())
        
    async def generate_video(self, audio_file, bg_music, video_folder):
        try:
            # Get volume adjustments based on active tab
            if self.notebook.select() == self.notebook.tabs()[0]:  # Story tab
                bg_volume = self.bg_volume_story / 100.0
                vo_volume = 1.0  # Story generation doesn't use voiceover adjustment
            else:  # Voiceover tab
                bg_volume = self.bg_volume_vo / 100.0
                vo_volume = self.vo_volume / 100.0
            
            # Load and adjust audio files
            vo_audio = AudioSegment.from_file(audio_file)
            bg_audio = AudioSegment.from_file(bg_music)
            
            # Apply volume adjustments
            vo_audio = vo_audio.apply_gain(20 * np.log10(vo_volume))
            bg_audio = bg_audio.apply_gain(20 * np.log10(bg_volume))
            
            # Export adjusted audio
            vo_audio.export("adjusted_vo.wav", format="wav")
            bg_audio.export("adjusted_bg.wav", format="wav")
            
            # Use adjusted files
            create_master_track("adjusted_vo.wav", "adjusted_bg.wav")
            
            # Transcribe audio
            self.log_output("Loading Whisper model...")
            model = whisper.load_model("base")
            self.update_progress(35)
            
            self.log_output("Transcribing audio...")
            result = model.transcribe(
                audio_file,
                language="en",
                word_timestamps=True,
                condition_on_previous_text=True,
                temperature=0.0
            )
            self.update_progress(45, "Processing transcription...")
            
            # Process transcription
            text_array = []
            for segment in result["segments"]:
                process_segment_with_words(segment, 60, None, text_array)
            
            # Show transcript editor
            self.log_output("Opening transcript editor...")
            editor = TranscriptEditor(self.root, text_array)
            self.root.wait_window(editor)
            
            if editor.edited:
                self.log_output("Transcript updated with edits")
            else:
                self.log_output("No changes made to transcript")
            
            self.update_progress(50, "Starting video compilation...")
            
            # Get output path based on active tab
            output_path = self.output_path_story.get() if self.notebook.select() == self.notebook.tabs()[0] else self.output_path_vo.get()
            
            # Create video compilation with progress updates
            await self.create_video_with_subtitles(video_folder, "master_track.wav", output_path, text_array)
            
            # Create clickable link
            self.create_file_link(os.path.abspath(output_path))
            
            # Cleanup
            self.log_output("Cleaning up temporary files...")
            os.remove("master_track.wav")
            if audio_file != "result.wav":
                os.remove(audio_file)
            os.remove("adjusted_vo.wav")
            os.remove("adjusted_bg.wav")

        except Exception as e:
            self.log_output(f"Error in generate_video: {str(e)}")
            raise e

    async def create_video_with_subtitles(self, video_folder, audio_path, output_path, text_array):
        """Create video with subtitles and progress updates"""
        try:
            # Initial video compilation
            self.log_output("Loading and processing video clips...")
            audio = AudioFileClip(audio_path)
            audio_duration = audio.duration

            video_files = [os.path.join(video_folder, f) for f in os.listdir(video_folder) 
                          if f.endswith('.mp4')]
            random.shuffle(video_files)

            self.log_output("Combining video clips...")
            video_clips = []
            current_duration = 0
            for i, video_file in enumerate(video_files):
                if current_duration >= audio_duration:
                    break
                self.log_output(f"Processing clip {i+1}/{len(video_files)}...")
                clip = VideoFileClip(video_file).subclip(0)
                video_clips.append(clip)
                current_duration += clip.duration
                self.update_progress(55 + (i/len(video_files))*10)

            self.log_output("Creating initial video compilation...")
            final_video = concatenate_videoclips(video_clips, method="compose")
            final_video = final_video.set_audio(audio)
            final_video = final_video.subclip(0, audio_duration)
            
            # Create temporary video
            self.log_output("Rendering temporary video...")
            temp_video = "temp_video.mp4"
            final_video.write_videofile(temp_video, codec="libx264", fps=60)
            self.update_progress(70, "Adding subtitles...")

            # Create frames with subtitles
            output_folder = "frames"
            os.makedirs(output_folder, exist_ok=True)
            
            # Extract frames and add subtitles
            self.log_output("Extracting frames and adding subtitles...")
            cap = cv2.VideoCapture(temp_video)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Constants for text rendering
            FONT = cv2.FONT_HERSHEY_DUPLEX
            FONT_SCALE_BASE = 2.0
            FONT_THICKNESS = 8
            STROKE_THICKNESS = 16
            target_height = height * 0.25
            max_width = width * 0.85
            min_width = width * 0.6
            
            # Animation settings
            ANIMATION_FRAMES = 3
            last_text = None
            animation_start = 0
            current_scale = FONT_SCALE_BASE * 2

            for frame_count in range(total_frames):
                if frame_count % 100 == 0:
                    progress = 70 + (frame_count/total_frames * 20)
                    self.update_progress(progress, f"Processing frame {frame_count}/{total_frames}")
                    self.root.update()

                ret, frame = cap.read()
                if not ret:
                    break

                # Find current text
                current_text = None
                for text_item in text_array:
                    if frame_count >= text_item[1] and frame_count <= text_item[2]:
                        if text_item[0] != last_text:
                            animation_start = frame_count
                            current_scale = FONT_SCALE_BASE
                        current_text = text_item[0]
                        last_text = current_text
                        break

                # If no text found, use last text
                if not current_text and last_text:
                    current_text = last_text

                if current_text:
                    # Handle long single words
                    if len(current_text.split()) == 1 and len(current_text) > 15:
                        current_text = current_text[:15] + "..."

                    # Calculate animation progress
                    if frame_count < animation_start + ANIMATION_FRAMES:
                        progress = (frame_count - animation_start) / ANIMATION_FRAMES
                        font_scale = FONT_SCALE_BASE + (FONT_SCALE_BASE * 2 - FONT_SCALE_BASE) * progress
                    else:
                        font_scale = FONT_SCALE_BASE * 2

                    # Get text size
                    text_size, _ = cv2.getTextSize(current_text, FONT, font_scale, FONT_THICKNESS)
                    
                    # Adjust font size to fit width and height
                    safety_margin = 20
                    while (text_size[0] > max_width - safety_margin or 
                           text_size[1] > target_height - safety_margin):
                        font_scale *= 0.98
                        text_size, _ = cv2.getTextSize(current_text, FONT, font_scale, FONT_THICKNESS)

                    # Calculate position for center of screen
                    text_x = int((width - text_size[0]) / 2)
                    text_y = int(height / 2 + text_size[1] / 3)

                    # Draw black stroke/outline
                    for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,1), (0,-1), (1,0), (-1,0)]:
                        cv2.putText(frame, current_text, 
                                  (text_x + dx*STROKE_THICKNESS//3, text_y + dy*STROKE_THICKNESS//3), 
                                  FONT, font_scale, (0, 0, 0), STROKE_THICKNESS)
                    
                    # Draw white text
                    cv2.putText(frame, current_text, (text_x, text_y), FONT, font_scale,
                               (255, 255, 255), FONT_THICKNESS)

                cv2.imwrite(os.path.join(output_folder, f"{frame_count}.jpg"), frame)

            cap.release()
            
            # Create final video
            self.log_output("Compiling final video...")
            self.update_progress(90, "Creating final video with subtitles...")
            images = sorted([img for img in os.listdir(output_folder) if img.endswith(".jpg")],
                           key=lambda x: int(x.split(".")[0]))
            
            clip = ImageSequenceClip([os.path.join(output_folder, image) for image in images], fps=60)
            clip = clip.set_audio(AudioFileClip(audio_path))
            
            self.log_output("Rendering final video...")
            clip.write_videofile(output_path)
            
            # Cleanup
            self.log_output("Cleaning up temporary files...")
            shutil.rmtree(output_folder)
            os.remove(temp_video)
            
            self.update_progress(100, "Video creation complete!")
            
        except Exception as e:
            self.log_output(f"Error in create_video_with_subtitles: {str(e)}")
            raise e

    def generate_from_voiceover(self):
        try:
            self.progress_var.set(0)
            self.output_text.delete(1.0, tk.END)
            
            if not os.path.exists(self.voiceover_path.get()):
                messagebox.showerror("Error", "Please select a voiceover file")
                return
                
            # No longer process audio here - let mixer handle it
            self.update_progress(30, "Creating video...")
            asyncio.run(self.generate_video(self.voiceover_path.get(), 
                                          self.bg_music_vo.get(), 
                                          self.video_folder_vo.get()))
            
            self.update_progress(100, "Video generation complete!")
            messagebox.showinfo("Success", "Video generated successfully!")
            self.status_var.set("Ready")
            
        except Exception as e:
            self.log_output(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error occurred")

    def browse_save_file(self, var):
        """Browse for save location"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if filename:
            var.set(filename)

    def create_file_link(self, filepath):
        """Create a clickable link in the output log"""
        import platform
        import subprocess
        
        def open_file_location():
            if platform.system() == "Windows":
                subprocess.run(['explorer', '/select,', filepath])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', '-R', filepath])
            else:  # Linux
                subprocess.run(['xdg-open', os.path.dirname(filepath)])
        
        # Create link text
        link_text = f"\nOutput saved to: {filepath}\n(Click here to open location)\n"
        
        # Insert link with tag
        self.output_text.tag_config("link", foreground="blue", underline=1)
        self.output_text.insert(tk.END, link_text, "link")
        
        # Bind click event
        self.output_text.tag_bind("link", "<Button-1>", lambda e: open_file_location())
        
        # Change cursor on hover
        self.output_text.tag_bind("link", "<Enter>", lambda e: self.output_text.config(cursor="hand2"))
        self.output_text.tag_bind("link", "<Leave>", lambda e: self.output_text.config(cursor=""))
        
        self.output_text.see(tk.END)

    def open_mixer_settings(self):
        """Open mixer settings window"""
        # Get the appropriate paths based on active tab
        if self.notebook.select() == self.notebook.tabs()[0]:  # Story tab
            if not hasattr(self, 'temp_vo_file'):
                messagebox.showerror("Error", "Please generate voiceover first")
                return
            
            vo_path = self.temp_vo_file  # Use the temporary voiceover file
            bg_path = self.bg_music_story.get()
            if not os.path.exists(bg_path):
                messagebox.showerror("Error", "Please select a background music file first")
                return
            initial_vo = 100
            initial_bg = self.bg_volume_story
        else:  # Voiceover tab
            vo_path = self.voiceover_path.get()
            bg_path = self.bg_music_vo.get()
            if not os.path.exists(vo_path) or not os.path.exists(bg_path):
                messagebox.showerror("Error", "Please select both audio files first")
                return
            initial_vo = self.vo_volume
            initial_bg = self.bg_volume_vo
        
        # Create mixer window
        mixer = MixerSettingsWindow(self.root, vo_path, bg_path, 
                                   vo_volume=initial_vo, 
                                   bg_volume=initial_bg)
        self.root.wait_window(mixer)
        
        # Store the saved volumes and get processed audio path if available
        vo_volume, bg_volume, processed_vo_path = mixer.get_volumes()
        if self.notebook.select() == self.notebook.tabs()[0]:  # Story tab
            self.vo_volume = vo_volume * 100
            self.bg_volume_story = bg_volume * 100
            if processed_vo_path != vo_path:  # If audio was processed
                self.temp_vo_file = processed_vo_path  # Update to use processed audio
        else:  # Voiceover tab
            self.vo_volume = vo_volume * 100
            self.bg_volume_vo = bg_volume * 100
            if processed_vo_path != vo_path:  # If audio was processed
                self.voiceover_path.set(processed_vo_path)  # Update to use processed audio

    def rephrase_story(self):
        """Open dialog to rephrase the story using AI"""
        try:
            story = self.story_text.get("1.0", tk.END).strip()
            if not story:
                messagebox.showerror("Error", "Please enter a story to rephrase")
                return
            
            # Check if ollama is available
            try:
                # Create and show dialog
                dialog = RephraseDialog(self.root, story)
                self.root.wait_window(dialog)
                
                # If user confirmed, update the story text
                if dialog.confirmed:
                    self.story_text.delete(1.0, tk.END)
                    self.story_text.insert(tk.END, dialog.rephrased_text)
            except ImportError:
                messagebox.showerror("Error", 
                    "Ollama is not installed. Please install it with: pip install ollama")
            except ConnectionError:
                messagebox.showerror("Error", 
                    "Could not connect to Ollama. Make sure the Ollama service is running.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def generate_story_voiceover(self):
        """Wrapper for async voiceover generation"""
        # Create and run event loop properly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._generate_story_voiceover())
        finally:
            loop.close()

    async def _generate_story_voiceover(self):
        """Generate TTS voiceover from story text"""
        try:
            story = self.story_text.get("1.0", tk.END).strip()
            if not story:
                messagebox.showerror("Error", "Please enter a story")
                return

            self.status_var.set("Generating voiceover...")
            self.log_output("Starting voiceover generation...")
            
            # Generate temporary voiceover file
            self.temp_vo_file = await process_story(story, False)
            if not self.temp_vo_file:
                messagebox.showerror("Error", "Failed to generate voiceover")
                return
            
            # Enable mixer and generate video buttons
            self.mixer_btn.config(state='normal')
            self.generate_video_btn.config(state='normal')
            
            self.status_var.set("Voiceover generated successfully")
            messagebox.showinfo("Success", "Voiceover generated successfully!")
            
        except Exception as e:
            self.log_output(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error occurred")

class TranscriptEditor(tk.Toplevel):
    def __init__(self, parent, transcript_data):
        super().__init__(parent)
        self.title("Edit Transcript")
        self.geometry("800x600")
        
        # Store transcript data
        self.transcript_data = transcript_data
        self.edited = False
        
        # Create widgets
        self.create_widgets()
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
    def create_widgets(self):
        # Instructions
        ttk.Label(self, text="Edit the transcript below. Each line represents a subtitle segment.").pack(padx=10, pady=5)
        
        # Create text editor
        self.text_editor = scrolledtext.ScrolledText(self, height=20)
        self.text_editor.pack(padx=10, pady=5, fill='both', expand=True)
        
        # Insert transcript data
        for segment in self.transcript_data:
            self.text_editor.insert(tk.END, f"{segment[0]}\n")
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(button_frame, text="Save", command=self.save_changes).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right', padx=5)
        
    def save_changes(self):
        # Get edited text
        edited_text = self.text_editor.get("1.0", tk.END).strip().split('\n')
        
        # Update transcript data with edited text while preserving timing
        for i, text in enumerate(edited_text):
            if i < len(self.transcript_data):
                self.transcript_data[i][0] = text
        
        self.edited = True
        self.destroy()
        
    def cancel(self):
        self.edited = False
        self.destroy()

class RephraseDialog(tk.Toplevel):
    def __init__(self, parent, original_story):
        super().__init__(parent)
        self.title("AI Rephrased Story")
        self.geometry("800x600")
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        self.original_story = original_story
        self.confirmed = False
        
        # Create widgets
        self.create_widgets()
        
        # Start rephrasing
        self.rephrase_story()
        
    def create_widgets(self):
        # Text editor
        self.text_editor = scrolledtext.ScrolledText(self, height=20)
        self.text_editor.pack(padx=10, pady=5, fill='both', expand=True)
        
        # Loading label
        self.status_label = ttk.Label(self, text="Rephrasing story with AI...")
        self.status_label.pack(pady=5)
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Confirm", command=self.confirm).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right', padx=5)
        
    def rephrase_story(self):
        try:
            # Get AI response
            try:
                response = ollama.chat(model="mistral", messages=[{
                    "role": "user",
                    "content": f"Rephrase this story to make it more engaging and natural, keep the same length and structure: {self.original_story}"
                }])
            except Exception as model_error:
                if "model not found" in str(model_error).lower():
                    self.status_label.config(
                        text="Model not found. Please run 'ollama pull mistral' in terminal first."
                    )
                    messagebox.showerror(
                        "Model Not Found", 
                        "The Mistral model needs to be downloaded first.\n\n"
                        "Please open a terminal and run:\nollama pull mistral"
                    )
                else:
                    self.status_label.config(text=f"Error: {str(model_error)}")
                return
            
            rephrased_story = response['message']['content']
            
            # Show only the rephrased version
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(tk.END, rephrased_story)
            
            self.status_label.config(text="You can edit the text before confirming")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            
    def confirm(self):
        # Get the edited text and save it
        self.rephrased_text = self.text_editor.get(1.0, tk.END).strip()
        self.confirmed = True
        self.destroy()
        
    def cancel(self):
        self.confirmed = False
        self.destroy()

def main():
    print("Please run the application using main.py")

if __name__ == "__main__":
    main() 