import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from pydub import AudioSegment
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pygame
import io
import threading
import os
import tempfile
import webrtcvad

class AudioPreviewWidget(ttk.Frame):
    def __init__(self, parent, label_text="Audio File"):
        super().__init__(parent)
        self.audio_data = None
        self.playing = False
        self.pygame_initialized = False
        
        # Initialize GUI elements
        self.setup_gui(label_text)
        
    def setup_gui(self, label_text):
        # Label
        ttk.Label(self, text=label_text).pack(pady=5)
        
        # Waveform display
        self.fig, self.ax = plt.subplots(figsize=(8, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill='x', expand=True)
        
        # Volume control
        volume_frame = ttk.Frame(self)
        volume_frame.pack(fill='x', pady=5)
        ttk.Label(volume_frame, text="Volume:").pack(side='left', padx=5)
        self.volume_var = tk.DoubleVar(value=100)
        self.volume_slider = ttk.Scale(
            volume_frame, 
            from_=0, 
            to=200, 
            orient='horizontal', 
            variable=self.volume_var,
            command=self.update_waveform
        )
        self.volume_slider.pack(side='left', fill='x', expand=True, padx=5)
        
        # Play button
        self.play_button = ttk.Button(
            self, 
            text="▶ Preview", 
            command=self.toggle_play,
            state='disabled'
        )
        self.play_button.pack(pady=5)
        
    def load_audio(self, audio_path):
        """Load audio file and display waveform"""
        try:
            self.audio_data = AudioSegment.from_file(audio_path)
            self.audio_path = audio_path
            self.update_waveform()
            self.play_button['state'] = 'normal'
            
            # Initialize pygame mixer if not already done
            if not self.pygame_initialized:
                pygame.mixer.init()
                self.pygame_initialized = True
            
            return True
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False
            
    def update_waveform(self, *args):
        """Update waveform display with current volume"""
        if self.audio_data is None:
            return
            
        # Clear previous plot
        self.ax.clear()
        
        # Get samples and apply volume
        samples = np.array(self.audio_data.get_array_of_samples())
        volume_factor = self.volume_var.get() / 100.0
        adjusted_samples = samples * volume_factor
        
        # Calculate normalized samples for visualization
        max_possible = 2**(self.audio_data.sample_width * 8 - 1)
        normalized = adjusted_samples / max_possible
        
        # Plot waveform
        time = np.linspace(0, len(normalized)/self.audio_data.frame_rate, len(normalized))
        self.ax.plot(time, normalized, linewidth=0.5, 
                    color='red' if np.max(np.abs(normalized)) > 1 else 'blue')
        
        # Set plot properties
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.set_xlabel('Time (s)')
        self.ax.grid(True, alpha=0.3)
        
        # Update canvas
        self.canvas.draw()
        
    def toggle_play(self):
        """Toggle audio preview playback"""
        if self.playing:
            pygame.mixer.music.stop()
            self.play_button['text'] = "▶ Preview"
            self.playing = False
        else:
            try:
                # Create a unique temporary file name
                temp_dir = tempfile.gettempdir()
                preview_file = os.path.join(temp_dir, f"preview_{id(self)}.wav")
                
                # Apply volume adjustment (clamped between 0.0 and 1.0)
                volume_factor = min(self.volume_var.get() / 100.0, 1.0)
                
                if self.volume_var.get() > 100:
                    # Apply gain for volumes over 100%
                    gain_db = 20 * np.log10(self.volume_var.get() / 100.0)
                    preview_audio = self.audio_data.apply_gain(gain_db)
                    preview_audio.export(preview_file, format="wav")
                    
                    # Stop any playing audio before loading new file
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    
                    pygame.mixer.music.load(preview_file)
                    pygame.mixer.music.set_volume(1.0)  # Full volume since gain is applied
                else:
                    # Normal volume playback
                    pygame.mixer.music.load(self.audio_path)
                    pygame.mixer.music.set_volume(volume_factor)
                
                pygame.mixer.music.play()
                self.play_button['text'] = "⏹ Stop"
                self.playing = True
                
                # Start monitoring thread with temp file reference
                self.preview_file = preview_file  # Store reference to current preview file
                threading.Thread(target=lambda: self.monitor_playback(preview_file), 
                               daemon=True).start()
                
            except Exception as e:
                print(f"Playback error: {e}")
                self.play_button['text'] = "▶ Preview"
                self.playing = False
                # Cleanup on error
                if 'preview_file' in locals() and os.path.exists(preview_file):
                    try:
                        os.remove(preview_file)
                    except:
                        pass

    def monitor_playback(self, temp_file):
        """Monitor audio playback and update button when finished"""
        try:
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            self.playing = False
            self.play_button['text'] = "▶ Preview"
            
            # Cleanup temp file after playback
            if os.path.exists(temp_file):
                try:
                    pygame.mixer.music.unload()
                    os.remove(temp_file)
                except:
                    pass
                
        except Exception as e:
            print(f"Monitor error: {e}")
            self.playing = False
            self.play_button['text'] = "▶ Preview"
        
    def get_volume_factor(self):
        """Get current volume factor for final rendering"""
        return self.volume_var.get() / 100.0 

class MixerSettingsWindow(tk.Toplevel):
    def __init__(self, parent, vo_path, bg_path, title="Audio Mixer", vo_volume=100, bg_volume=100):
        super().__init__(parent)
        self.title(title)
        self.geometry("800x700")  # Made taller for two waveforms
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        # Initialize audio
        self.vo_data = None
        self.bg_data = None
        self.vo_path = vo_path
        self.bg_path = bg_path
        self.playing = False
        self.pygame_initialized = False
        
        # Save initial volumes
        self.saved_vo_volume = vo_volume
        self.saved_bg_volume = bg_volume
        
        # Create widgets
        self.create_widgets()
        
        # Load audio
        if vo_path:
            self.vo_data = AudioSegment.from_file(vo_path)
        if bg_path:
            self.bg_data = AudioSegment.from_file(bg_path)
            
        # Update displays
        self.update_vo_waveform()
        self.update_bg_waveform()
            
    def create_widgets(self):
        # Voiceover section
        vo_frame = ttk.LabelFrame(self, text="Voiceover")
        vo_frame.pack(fill='x', padx=10, pady=5)
        
        # Voiceover waveform
        self.vo_fig, self.vo_ax = plt.subplots(figsize=(8, 2))
        self.vo_canvas = FigureCanvasTkAgg(self.vo_fig, master=vo_frame)
        self.vo_canvas.get_tk_widget().pack(fill='x', expand=True, padx=10, pady=5)
        
        # Voiceover volume control
        self.vo_db_label = ttk.Label(vo_frame, text="0 dB", font=("Arial", 12, "bold"))
        self.vo_db_label.pack(anchor='e', padx=10)
        
        scale_frame = ttk.Frame(vo_frame)
        scale_frame.pack(fill='x', padx=10)
        ttk.Label(scale_frame, text="-60 dB").pack(side='left')
        ttk.Label(scale_frame, text="0 dB").pack(side='left', padx=(180, 0))
        ttk.Label(scale_frame, text="+20 dB").pack(side='right')
        
        self.vo_volume = tk.DoubleVar(value=self.saved_vo_volume)
        self.vo_slider = ttk.Scale(
            vo_frame,
            from_=0.1,
            to=1000,
            orient='horizontal',
            variable=self.vo_volume,
            command=self.update_vo_volume
        )
        self.vo_slider.pack(fill='x', padx=10, pady=5)
        
        # Deadspace removal button for voiceover
        self.vo_deadspace_btn = ttk.Button(
            vo_frame,
            text="Remove Deadspace (Experimental)",
            command=self.toggle_deadspace_removal
        )
        self.vo_deadspace_btn.pack(fill='x', padx=10, pady=5)
        
        # Store original audio for restoration
        self.original_vo_data = self.vo_data
        self.deadspace_removed = False
        
        # Background Music section
        bg_frame = ttk.LabelFrame(self, text="Background Music")
        bg_frame.pack(fill='x', padx=10, pady=5)
        
        # Background music waveform
        self.bg_fig, self.bg_ax = plt.subplots(figsize=(8, 2))
        self.bg_canvas = FigureCanvasTkAgg(self.bg_fig, master=bg_frame)
        self.bg_canvas.get_tk_widget().pack(fill='x', expand=True, padx=10, pady=5)
        
        # Background music volume control
        self.bg_db_label = ttk.Label(bg_frame, text="0 dB", font=("Arial", 12, "bold"))
        self.bg_db_label.pack(anchor='e', padx=10)
        
        scale_frame = ttk.Frame(bg_frame)
        scale_frame.pack(fill='x', padx=10)
        ttk.Label(scale_frame, text="-60 dB").pack(side='left')
        ttk.Label(scale_frame, text="0 dB").pack(side='left', padx=(180, 0))
        ttk.Label(scale_frame, text="+20 dB").pack(side='right')
        
        self.bg_volume = tk.DoubleVar(value=self.saved_bg_volume)
        self.bg_slider = ttk.Scale(
            bg_frame,
            from_=0.1,
            to=1000,
            orient='horizontal',
            variable=self.bg_volume,
            command=self.update_bg_volume
        )
        self.bg_slider.pack(fill='x', padx=10, pady=5)
        
        # Preview controls
        control_frame = ttk.Frame(self)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.vo_preview_btn = ttk.Button(
            control_frame,
            text="Preview Voiceover",
            command=self.preview_voiceover
        )
        self.vo_preview_btn.pack(side='left', padx=5)
        
        self.bg_preview_btn = ttk.Button(
            control_frame,
            text="Preview Music",
            command=self.preview_background
        )
        self.bg_preview_btn.pack(side='left', padx=5)
        
        self.mix_preview_btn = ttk.Button(
            control_frame,
            text="Preview Mix",
            command=self.preview_mix
        )
        self.mix_preview_btn.pack(side='left', padx=5)
        
        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save Changes", 
                  command=self.save_changes).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel",
                  command=self.cancel).pack(side='right', padx=5)

    def update_vo_volume(self, *args):
        volume = self.vo_volume.get()
        if volume > 0:
            db = 20 * np.log10(volume / 100.0)
            self.vo_db_label.config(text=f"{db:.1f} dB")
        else:
            self.vo_db_label.config(text="-∞ dB")
        self.update_vo_waveform()
        
    def update_bg_volume(self, *args):
        volume = self.bg_volume.get()
        if volume > 0:
            db = 20 * np.log10(volume / 100.0)
            self.bg_db_label.config(text=f"{db:.1f} dB")
        else:
            self.bg_db_label.config(text="-∞ dB")
        self.update_bg_waveform()

    def update_vo_waveform(self):
        self._update_waveform(self.vo_data, self.vo_volume.get(), 
                            self.vo_ax, self.vo_canvas)
        
    def update_bg_waveform(self):
        self._update_waveform(self.bg_data, self.bg_volume.get(), 
                            self.bg_ax, self.bg_canvas)
        
    def _update_waveform(self, audio_data, volume, ax, canvas):
        if audio_data is None:
            return
            
        ax.clear()
        samples = np.array(audio_data.get_array_of_samples())
        volume_factor = volume / 100.0
        adjusted_samples = samples * volume_factor
        
        max_possible = 2**(audio_data.sample_width * 8 - 1)
        normalized = adjusted_samples / max_possible
        
        time = np.linspace(0, len(normalized)/audio_data.frame_rate, len(normalized))
        ax.plot(time, normalized, linewidth=0.5,
               color='red' if np.max(np.abs(normalized)) > 1 else 'blue')
        
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlabel('Time (s)')
        ax.grid(True, alpha=0.3)
        canvas.draw()

    def preview_voiceover(self):
        """Preview voiceover with current volume"""
        if self.playing:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.vo_preview_btn.config(text="Preview Voiceover")
            self.bg_preview_btn.config(state='normal')
            self.mix_preview_btn.config(state='normal')
            self.playing = False
        else:
            self._preview_audio(self.vo_data, self.vo_volume.get(), self.vo_preview_btn)
            self.bg_preview_btn.config(state='disabled')
            self.mix_preview_btn.config(state='disabled')
        
    def preview_background(self):
        """Preview background music with current volume"""
        if self.playing:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.bg_preview_btn.config(text="Preview Music")
            self.vo_preview_btn.config(state='normal')
            self.mix_preview_btn.config(state='normal')
            self.playing = False
        else:
            self._preview_audio(self.bg_data, self.bg_volume.get(), self.bg_preview_btn)
            self.vo_preview_btn.config(state='disabled')
            self.mix_preview_btn.config(state='disabled')
        
    def preview_mix(self):
        """Preview both tracks mixed together"""
        if self.playing:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.mix_preview_btn.config(text="Preview Mix")
            self.vo_preview_btn.config(state='normal')
            self.bg_preview_btn.config(state='normal')
            self.playing = False
            return
        
        if not self.vo_data or not self.bg_data:
            return
        
        try:
            # Create mix with current volume settings
            vo_adjusted = self.vo_data.apply_gain(20 * np.log10(self.vo_volume.get() / 100.0))
            bg_adjusted = self.bg_data.apply_gain(20 * np.log10(self.bg_volume.get() / 100.0))
            
            # Mix the tracks
            mixed = vo_adjusted.overlay(bg_adjusted)
            
            # Export to temp file and play
            temp_dir = tempfile.gettempdir()
            preview_file = os.path.join(temp_dir, f"preview_mix_{id(self)}.wav")
            mixed.export(preview_file, format="wav")
            
            if not self.pygame_initialized:
                pygame.mixer.init()
                self.pygame_initialized = True
                
            pygame.mixer.music.load(preview_file)
            pygame.mixer.music.play()
            
            self.mix_preview_btn.config(text="⏹ Stop Mix")
            self.vo_preview_btn.config(state='disabled')
            self.bg_preview_btn.config(state='disabled')
            self.playing = True
            
            # Monitor playback
            threading.Thread(target=lambda: self._monitor_playback(preview_file, 
                                                                 self.mix_preview_btn,
                                                                 "Preview Mix"),
                           daemon=True).start()
                           
        except Exception as e:
            print(f"Mix preview error: {e}")
            self.mix_preview_btn.config(text="Preview Mix")
            self.vo_preview_btn.config(state='normal')
            self.bg_preview_btn.config(state='normal')
            self.playing = False

    def _preview_audio(self, audio_data, volume, button):
        if not audio_data:
            return
        
        try:
            temp_dir = tempfile.gettempdir()
            preview_file = os.path.join(temp_dir, f"preview_{id(self)}.wav")
            
            # Apply gain
            gain_db = 20 * np.log10(volume / 100.0)
            preview_audio = audio_data.apply_gain(gain_db)
            preview_audio.export(preview_file, format="wav")
            
            if not self.pygame_initialized:
                pygame.mixer.init()
                self.pygame_initialized = True
                
            pygame.mixer.music.load(preview_file)
            pygame.mixer.music.play()
            
            original_text = button.cget('text')
            button.config(text="⏹ Stop")
            self.playing = True
            
            # Monitor playback
            threading.Thread(target=lambda: self._monitor_playback(preview_file, 
                                                                 button,
                                                                 original_text),
                           daemon=True).start()
                           
        except Exception as e:
            print(f"Preview error: {e}")
            button.config(text=original_text)
            self.playing = False

    def _monitor_playback(self, temp_file, button, original_text):
        try:
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            self.playing = False
            button.config(text=original_text)
            
            if os.path.exists(temp_file):
                try:
                    pygame.mixer.music.unload()
                    os.remove(temp_file)
                except:
                    pass
                    
        except Exception as e:
            print(f"Monitor error: {e}")
            self.playing = False
            button.config(text=original_text)

    def save_changes(self):
        """Save current settings and close window"""
        # Save volume settings
        self.saved_vo_volume = self.vo_volume.get()
        self.saved_bg_volume = self.bg_volume.get()
        
        # If deadspace was removed, save the processed audio
        if self.deadspace_removed:
            # Create a temporary file for the processed audio
            temp_dir = tempfile.gettempdir()
            processed_vo_file = os.path.join(temp_dir, f"processed_vo_{id(self)}.wav")
            self.vo_data.export(processed_vo_file, format="wav")
            self.vo_path = processed_vo_file  # Update the path to use processed audio
        
        self.destroy()

    def cancel(self):
        if self.deadspace_removed:
            self.vo_data = self.original_vo_data
        self.vo_volume.set(self.saved_vo_volume)
        self.bg_volume.set(self.saved_bg_volume)
        self.destroy()
        
    def get_volumes(self):
        """Get saved volume factors and current voiceover path"""
        return (self.saved_vo_volume / 100.0, 
                self.saved_bg_volume / 100.0, 
                self.vo_path)  # Return the current voiceover path

    def toggle_deadspace_removal(self):
        """Toggle deadspace removal for voiceover"""
        try:
            if not self.deadspace_removed:
                # Store original audio if not already stored
                if self.original_vo_data is None:
                    self.original_vo_data = self.vo_data
                
                # Process audio to remove deadspace while maintaining quality
                self.vo_data = self.remove_deadspace_hq(self.vo_data)
                self.vo_deadspace_btn.config(text="Restore Original Audio")
                self.deadspace_removed = True
            else:
                # Restore original audio
                self.vo_data = self.original_vo_data
                self.vo_deadspace_btn.config(text="Remove Deadspace (Experimental)")
                self.deadspace_removed = False
            
            # Update waveform display
            self.update_vo_waveform()
            
        except Exception as e:
            print(f"Error in deadspace removal: {e}")
            messagebox.showerror("Error", f"Failed to process audio: {str(e)}")

    def remove_deadspace_hq(self, audio):
        """Remove silence from audio using VAD while maintaining quality"""
        # Create a working copy for VAD processing by exporting and reimporting
        temp_file = os.path.join(tempfile.gettempdir(), f"temp_vad_{id(self)}.wav")
        try:
            # Create working copy by exporting and reimporting
            audio.export(temp_file, format="wav")
            vad_audio = AudioSegment.from_wav(temp_file)
            
            # Convert working copy to format needed for VAD
            if vad_audio.channels > 1:
                vad_audio = vad_audio.set_channels(1)
            if vad_audio.sample_width != 2:
                vad_audio = vad_audio.set_sample_width(2)
            if vad_audio.frame_rate != 16000:
                vad_audio = vad_audio.set_frame_rate(16000)
            
            # Convert audio to raw data
            audio_data = np.array(vad_audio.get_array_of_samples())
            
            # Initialize VAD
            vad = webrtcvad.Vad()
            vad.set_mode(2)  # Aggressiveness level (0-3)
            
            # Process in 10ms frames
            frame_duration = 10  # ms
            frame_size = int(vad_audio.frame_rate * frame_duration / 1000)
            num_frames = len(audio_data) // frame_size
            
            # Calculate milliseconds per sample for original audio
            ms_per_sample = 1000 / audio.frame_rate
            
            # Identify frames with speech and keep track of timestamps
            speech_segments = []
            for i in range(num_frames):
                frame = audio_data[i*frame_size:(i+1)*frame_size].tobytes()
                if vad.is_speech(frame, vad_audio.frame_rate):
                    # Convert frame indices to timestamps for original audio
                    start_ms = int(i * frame_duration)
                    end_ms = int((i + 1) * frame_duration)
                    speech_segments.append((start_ms, end_ms))
            
            # Merge consecutive segments
            merged_segments = []
            if speech_segments:
                current_start, current_end = speech_segments[0]
                for start, end in speech_segments[1:]:
                    if start <= current_end + 50:  # Add small buffer between segments
                        current_end = end
                    else:
                        merged_segments.append((current_start, current_end))
                        current_start, current_end = start, end
                merged_segments.append((current_start, current_end))
            
            # Extract segments from original high-quality audio
            if merged_segments:
                speech_frames = [audio[start:end] for start, end in merged_segments]
                return sum(speech_frames[1:], speech_frames[0])
            
            return audio
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
