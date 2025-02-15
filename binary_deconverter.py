import cv2
import numpy as np
import os
import json
import struct
from pytube import YouTube

def video_to_binary(video_path):
    """Convert video back to binary data"""
    cap = cv2.VideoCapture(video_path)
    binary_data = []
    
    # Get video dimensions
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video dimensions: {width}x{height}")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Threshold to get binary values (0 or 1)
            _, binary = cv2.threshold(gray, 128, 1, cv2.THRESH_BINARY)
            
            # Process the frame row by row to maintain correct order
            for row in binary:
                current_byte = 0
                bit_count = 0
                
                for pixel in row:
                    current_byte = (current_byte << 1) | pixel
                    bit_count += 1
                    
                    if bit_count == 8:
                        binary_data.append(current_byte)
                        current_byte = 0
                        bit_count = 0
            
            print(f"Processing frame {int(cap.get(cv2.CAP_PROP_POS_FRAMES))}", end='\r')
    
    finally:
        cap.release()
    
    print("\nTotal bytes recovered:", len(binary_data))
    return bytes(binary_data)

def extract_files(binary_data, output_dir):
    """Extract files from binary data using metadata"""
    # Read metadata length
    metadata_len = struct.unpack('!I', binary_data[:4])[0]
    
    # Extract metadata
    metadata = json.loads(binary_data[4:4+metadata_len].decode())
    
    # Extract files
    current_pos = 4 + metadata_len
    for filepath, filesize in metadata.items():
        # Create full path including root folder
        full_path = os.path.join(output_dir, filepath)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'wb') as f:
            f.write(binary_data[current_pos:current_pos+filesize])
        current_pos += filesize
        print(f"Extracted: {filepath}")

if __name__ == "__main__":
    # Get input type
    input_type = input("Select input type:\n1. Local video file\n2. YouTube video\nEnter choice (1/2): ")
    
    if input_type == "1":
        video_path = input("Enter the path to the binary visualization video: ").strip('"')
        if not os.path.exists(video_path):
            print(f"Error: Video file '{video_path}' does not exist!")
            exit(1)
    
    elif input_type == "2":
        url = input("Enter YouTube video URL: ")
        try:
            print("Downloading YouTube video...")
            yt = YouTube(url)
            # Get highest resolution stream
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            if not stream:
                print("Error: No suitable video stream found!")
                exit(1)
            
            video_path = "temp_youtube_video.mp4"
            stream.download(filename=video_path)
            print("Video downloaded successfully!")
            
        except Exception as e:
            print(f"Error downloading YouTube video: {str(e)}")
            exit(1)
    
    else:
        print("Invalid choice!")
        exit(1)

    output_dir = input("Enter the output directory path: ").strip('"')
    os.makedirs(output_dir, exist_ok=True)
    
    print("Converting video back to binary data...")
    binary_data = video_to_binary(video_path)
    
    print(f"\nExtracted binary size: {len(binary_data)/1024:.2f} KB")
    print(f"\nExtracting files to: {output_dir}")
    
    try:
        extract_files(binary_data, output_dir)
        print("\nExtraction complete!")
    except Exception as e:
        print(f"Error during extraction: {str(e)}")

    # Clean up temp file if it was from YouTube
    if input_type == "2" and os.path.exists(video_path):
        os.remove(video_path)
