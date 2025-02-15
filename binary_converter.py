import numpy as np
import cv2
import os
import json
import struct
from pytube import YouTube

def process_input_path(path):
    """Process file or folder and return binary data with metadata"""
    files_data = {}
    total_binary = b''
    
    if os.path.isfile(path):
        # Single file - put directly in output folder
        filename = os.path.basename(path)
        with open(path, 'rb') as f:
            content = f.read()
            files_data[filename] = len(content)
            total_binary = content
    else:
        # Directory - maintain single folder structure
        root_folder = os.path.basename(path)
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                # Create path relative to input folder and add under root folder
                rel_path = os.path.relpath(file_path, path)
                target_path = os.path.join(root_folder, rel_path)
                with open(file_path, 'rb') as f:
                    content = f.read()
                    files_data[target_path] = len(content)
                    total_binary += content

    # Create metadata
    metadata = json.dumps(files_data).encode()
    
    # Format: [metadata_length(4 bytes)][metadata_json][files_binary_data]
    return struct.pack('!I', len(metadata)) + metadata + total_binary

def get_output_video_path():
    """Get path for saving or uploading the video"""
    choice = input("Do you want to:\n1. Save video locally\n2. Upload to YouTube\nEnter choice (1/2): ")
    if choice == "1":
        return input("Enter output video path (default: binary_visualization.mp4): ").strip('"') or "binary_visualization.mp4"
    elif choice == "2":
        print("Note: You need to be logged in to YouTube to upload")
        print("This feature requires YouTube Data API setup")
        return None
    return "binary_visualization.mp4"

def get_video_settings():
    """Get video settings from user"""
    orientation = input("Select video orientation:\n1. Landscape (1920x1080)\n2. Portrait (1080x1920)\nEnter choice (1/2): ")
    
    if orientation == "1":
        resolution = (1920, 1080)
    else:
        resolution = (1080, 1920)
    
    fps = int(input("Enter FPS (default 60): ") or "60")
    return resolution, fps

def create_binary_video(binary_data, output_path="binary_visualization.mp4", fps=60, resolution=(1920, 1080)):
    """Convert binary data to video with specified resolution"""
    width, height = resolution
    
    # Convert binary data to bits
    binary_list = []
    for byte in binary_data:
        # Ensure we get exactly 8 bits per byte
        bits = format(byte, '08b')
        binary_list.extend([1 if bit == '1' else 0 for bit in bits])
    
    # Pad the binary list to fit complete frames
    pixels_per_frame = width * height
    if len(binary_list) % pixels_per_frame != 0:
        padding = pixels_per_frame - (len(binary_list) % pixels_per_frame)
        binary_list.extend([0] * padding)
    
    total_frames = len(binary_list) // pixels_per_frame
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    try:
        for frame_num in range(total_frames):
            frame = np.zeros((height, width), dtype=np.uint8)
            
            # Get binary data for this frame
            start_idx = frame_num * pixels_per_frame
            end_idx = start_idx + pixels_per_frame
            frame_data = binary_list[start_idx:end_idx]
            
            # Fill frame row by row
            for i, bit in enumerate(frame_data):
                row = i // width
                col = i % width
                frame[row, col] = 255 if bit else 0
            
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            out.write(frame_bgr)
            
            if frame_num % 10 == 0:
                print(f"Processing frame {frame_num + 1}/{total_frames}")
    
    finally:
        out.release()
    
    return total_frames

def download_from_youtube(url):
    """Download YouTube video with custom headers and error handling"""
    try:
        # Custom headers to avoid 403 error
        custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create YouTube object with custom headers
        yt = YouTube(
            url,
            use_oauth=True,
            allow_oauth_cache=True,
            on_progress_callback=lambda stream, chunk, bytes_remaining: print(
                f"Downloading: {(1-bytes_remaining/stream.filesize)*100:.1f}%", end='\r'
            )
        )
        
        # Get highest resolution stream
        print("Getting available streams...")
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not stream:
            raise Exception("No suitable video stream found!")
        
        print(f"Found stream: {stream.resolution} ({stream.filesize/1024/1024:.1f} MB)")
        temp_file = "temp_youtube_video.mp4"
        
        print("Downloading video...")
        stream.download(filename=temp_file)
        print("\nDownload complete!")
        
        with open(temp_file, 'rb') as f:
            data = f.read()
        
        os.remove(temp_file)
        return data
        
    except Exception as e:
        print(f"\nError downloading video: {str(e)}")
        print("Try these troubleshooting steps:")
        print("1. Check if the video is available in your region")
        print("2. Check your internet connection")
        print("3. Try a different video URL")
        raise

if __name__ == "__main__":
    # Get input type
    input_type = input("Select input type:\n1. Local file/folder\n2. YouTube video\nEnter choice (1/2): ")
    
    if input_type == "1":
        # Process local file/folder
        input_path = input("Enter the path to file or folder to convert: ").strip('"')
        if not os.path.exists(input_path):
            print(f"Error: Path '{input_path}' does not exist!")
            exit(1)
        
        print(f"Processing: {input_path}")
        binary_data = process_input_path(input_path)
    
    elif input_type == "2":
        # Download from YouTube
        url = input("Enter YouTube video URL: ")
        try:
            binary_data = download_from_youtube(url)
        except Exception:
            exit(1)
    
    else:
        print("Invalid choice!")
        exit(1)

    print(f"Total size: {len(binary_data)/1024:.2f} KB")
    
    # Get output path
    output_path = get_output_video_path()
    
    # Get video settings
    resolution, fps = get_video_settings()
    
    print("\nCreating video from binary data...")
    total_frames = create_binary_video(binary_data, output_path, fps, resolution)
    
    print(f"\nVideo creation complete!")
    print(f"Total frames: {total_frames}")
    print(f"Video duration: {total_frames/60:.2f} seconds")
    print(f"Output saved as: {output_path}")