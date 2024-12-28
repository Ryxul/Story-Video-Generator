import asyncio
import edge_tts
import ollama
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, ImageSequenceClip
import numpy as np
import webrtcvad
import shutil
import os
import random
import cv2

async def text_to_speech(text, output_file="story_audio.wav"):
    """Convert text to speech using Edge TTS"""
    try:
        # Initialize Edge TTS with a voice
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        
        # Generate speech to mp3 first
        temp_mp3 = "temp_speech.mp3"
        
        print("Generating speech...")
        await communicate.save(temp_mp3)
        
        if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) == 0:
            raise Exception("Failed to generate audio file")
            
        print("Converting to WAV format...")
        # Convert to WAV using pydub
        audio = AudioSegment.from_mp3(temp_mp3)
        
        # Ensure audio has content
        if len(audio) == 0:
            raise Exception("Generated audio has no content")
            
        # Export as WAV with specific parameters
        audio.export(output_file, format="wav", parameters=["-ac", "1", "-ar", "16000"])
        
        # Verify the output file
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise Exception("Failed to create WAV file")
            
        # Clean up temp file
        os.remove(temp_mp3)
        
        print(f"Audio generated successfully: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)
        if os.path.exists(output_file):
            os.remove(output_file)
        raise Exception(f"Failed to generate audio: {str(e)}")

async def process_story(story_text, rephrase=False):
    """Process input story and convert to audio"""
    if rephrase:
        print("Rephrasing story...")
        try:
            story_text = rephrase_with_ollama(story_text)
            print("Story rephrased successfully")
        except Exception as e:
            print(f"Error rephrasing story: {e}")
            print("Using original story text")

    # Convert to speech
    try:
        print("Starting text-to-speech conversion...")
        if not story_text or len(story_text.strip()) == 0:
            raise Exception("Empty story text")
            
        audio_file = await text_to_speech(story_text)
        if not audio_file or not os.path.exists(audio_file):
            raise Exception("Failed to generate audio file")
            
        # No longer process audio here - let the mixer handle it
        print("Audio generation complete")
        return audio_file
        
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None

def create_master_track(voiceover_path, music_path, output_path="master_track.wav"):
    """Combine voiceover and background music"""
    voiceover_track = AudioSegment.from_file(voiceover_path, format="wav") + 5
    music_track = AudioSegment.from_file(music_path, format="wav")
    
    temp_master_track = voiceover_track.overlay(music_track, position=0)
    master_track = temp_master_track[:len(voiceover_track)]
    
    master_track.export(output_path, format="wav")
    print(f"Master track saved as '{output_path}'")

def create_video_compilation(video_folder, audio_path, output_path, text_array=None):
    """Create video compilation from folder of clips matched to audio length"""
    print('Creating video compilation')
    
    # Validate video folder
    if not os.path.exists(video_folder):
        raise Exception(f"Video folder '{video_folder}' does not exist")
    
    # Get video files
    video_files = [os.path.join(video_folder, f) for f in os.listdir(video_folder) 
                  if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    # Check if any video files were found
    if not video_files:
        raise Exception(
            f"No video files found in '{video_folder}'. "
            "Please add some video files (MP4, AVI, MOV, or MKV format) to this folder."
        )
    
    # Load audio
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    # Shuffle video files
    random.shuffle(video_files)

    # Add clips until reaching audio duration
    video_clips = []
    current_duration = 0
    
    for video_file in video_files:
        if current_duration >= audio_duration:
            break
        try:
            clip = VideoFileClip(video_file).subclip(0)
            video_clips.append(clip)
            current_duration += clip.duration
        except Exception as e:
            print(f"Warning: Could not load video file '{video_file}': {str(e)}")
            continue
    
    # Check if we have any valid video clips
    if not video_clips:
        raise Exception(
            "Could not load any valid video clips. "
            "Please ensure your video files are not corrupted and in a supported format."
        )

    # Create final video
    final_video = concatenate_videoclips(video_clips, method="compose")
    final_video = final_video.set_audio(audio)
    final_video = final_video.subclip(0, audio_duration)
    
    if text_array:
        # First create the video without subtitles
        temp_video = "temp_video.mp4"
        final_video.write_videofile(temp_video, codec="libx264", fps=60)
        
        # Create frames with subtitles
        output_folder = "frames"
        os.makedirs(output_folder, exist_ok=True)
        
        # Constants for text rendering
        FONT = cv2.FONT_HERSHEY_DUPLEX
        FONT_SCALE_BASE = 2.0
        FONT_THICKNESS = 8
        STROKE_THICKNESS = 16
        
        create_subtitled_frames(temp_video, text_array, output_folder, FONT, 
                              FONT_SCALE_BASE, FONT_THICKNESS, STROKE_THICKNESS)
        
        # Create final video with subtitles
        create_final_video(output_folder, 60, audio_path, output_path)
        
        # Cleanup
        shutil.rmtree(output_folder)
        os.remove(temp_video)
    else:
        final_video.write_videofile(output_path, codec="libx264", fps=60)
    
    print(f"Video compilation saved as '{output_path}'")

def create_subtitled_frames(video_path, text_array, output_folder, FONT, FONT_SCALE_BASE, FONT_THICKNESS, STROKE_THICKNESS):
    """Create individual frames with subtitles"""
    print('Extracting frames')
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = 0

    # Calculate the target text height (percentage of screen height)
    target_height = height * 0.25  # Increased for larger text
    
    # Define text area bounds
    max_width = width * 0.85  # Maximum width for text (85% of screen width)
    min_width = width * 0.6  # Minimum width for text (60% of screen width)

    # Animation settings
    ANIMATION_FRAMES = 3  # Number of frames for animation
    last_text = None
    animation_start = 0
    current_scale = FONT_SCALE_BASE * 2  # Base scale for current text

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Find current text
        current_text = None
        for text_item in text_array:
            if frame_count >= text_item[1] and frame_count <= text_item[2]:
                if text_item[0] != last_text:
                    animation_start = frame_count
                    current_scale = FONT_SCALE_BASE  # Start small
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
            text_y = int(height / 2 + text_size[1] / 3)  # Slightly above center

            # Draw black stroke/outline (draw text in 8 directions)
            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,1), (0,-1), (1,0), (-1,0)]:
                cv2.putText(frame, current_text, 
                          (text_x + dx*STROKE_THICKNESS//3, text_y + dy*STROKE_THICKNESS//3), 
                          FONT, font_scale, (0, 0, 0), STROKE_THICKNESS)
            
            # Draw white text
            cv2.putText(frame, current_text, (text_x, text_y), FONT, font_scale,
                       (255, 255, 255), FONT_THICKNESS)

        cv2.imwrite(os.path.join(output_folder, f"{frame_count}.jpg"), frame)
        frame_count += 1

    cap.release()
    print('Frames extracted')

def create_final_video(frames_folder, fps, audio_path, output_path):
    """Compile frames into final video with audio"""
    print('Creating video')
    images = sorted([img for img in os.listdir(frames_folder) if img.endswith(".jpg")],
                   key=lambda x: int(x.split(".")[0]))
    
    clip = ImageSequenceClip([os.path.join(frames_folder, image) for image in images], fps=fps)
    audio = AudioFileClip(audio_path)
    clip = clip.set_audio(audio)
    clip.write_videofile(output_path)

def process_segment_with_words(segment, fps, max_width, text_array):
    """Process segments with word-level timing for better accuracy"""
    if not segment.get("words"):
        return

    current_line = []
    line_start = None
    last_text = None
    
    for word in segment["words"]:
        if line_start is None:
            line_start = word["start"]
            
        current_line.append(word["word"].strip())
        
        # Check if we should start a new line (max 3 words)
        if len(current_line) >= 3:
            text = " ".join(current_line)
            start_frame = int(line_start * fps)
            end_frame = int(word["end"] * fps)  # Changed from start to end
            
            if text.strip():
                # Fill any gap from last segment
                if last_text is not None and start_frame > last_text[2] + 2:
                    text_array.append([last_text[0], last_text[2], start_frame])
                
                text_array.append([text.strip(), start_frame, end_frame])
                last_text = [text.strip(), start_frame, end_frame]
            
            # Reset for next line
            current_line = []
            line_start = word["end"]  # Start from end of last word
    
    # Add remaining words
    if current_line:
        text = " ".join(current_line)
        start_frame = int(line_start * fps)
        end_frame = int(segment["end"] * fps)
        if text.strip():
            if last_text is not None and start_frame > last_text[2] + 2:
                text_array.append([last_text[0], last_text[2], start_frame])
            text_array.append([text.strip(), start_frame, end_frame]) 