import os
import json
import time
from pathlib import Path
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline
import torch
from pydub import AudioSegment

# Define base directories
BASE_DIR = Path("./data")
RAW_DIR = BASE_DIR / "raw"
PROCESSED_DIR = BASE_DIR / "processed"
OUTPUT_DIR = BASE_DIR / "output"
VIDEO_DIR = RAW_DIR / "videos"
SLIDES_DIR = RAW_DIR / "slides"
AUDIO_DIR = PROCESSED_DIR / "audio"
TRANSCRIPTS_DIR = PROCESSED_DIR / "transcripts"
NOTES_DIR = OUTPUT_DIR / "lecture_notes"

# Ensure directories exist
for directory in [BASE_DIR, RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, VIDEO_DIR, SLIDES_DIR, AUDIO_DIR, TRANSCRIPTS_DIR, NOTES_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

def load_whisper_model(model_id="openai/whisper-small"):
    """Load a Whisper model for speech recognition"""
    try:
        print(f"Loading speech-to-text model: {model_id}")
        
        # Load processor
        processor = AutoProcessor.from_pretrained(model_id)
        
        # Load model
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Create a pipeline
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor
        )
        
        print(f"Speech-to-text model loaded: {model_id}")
        return pipe
    except Exception as e:
        print(f"Error loading whisper model: {e}")
        return None

def continue_transcription(whisper_model=None):
    """
    Continue transcribing audio files that haven't been processed yet
    
    Args:
        whisper_model: Pre-loaded Whisper model, will load if None
    
    Returns:
        Dictionary of transcription results
    """
    print("Starting continued transcription process...")
    
    # 1. Load the transcription model if not provided
    if whisper_model is None:
        print("Loading Whisper model...")
        whisper_model = load_whisper_model()
        if whisper_model is None:
            return {"error": "Failed to load Whisper model"}
    
    # 2. Get the list of audio files
    audio_files = list(AUDIO_DIR.glob("*.wav"))
    
    # 3. Get list of already transcribed files
    existing_transcripts = [path.stem.replace("_transcript", "") for path in TRANSCRIPTS_DIR.glob("*_transcript.json")]
    
    # 4. Filter for untranscribed files
    untranscribed_files = [audio for audio in audio_files if audio.stem not in existing_transcripts]
    
    total_files = len(untranscribed_files)
    if total_files == 0:
        print("No remaining audio files to transcribe")
        return {"message": "All files already transcribed"}
    
    print(f"Found {total_files} audio files that need transcription")
    
    # 5. Process each file
    results = []
    success_count = 0
    
    for i, audio_path in enumerate(untranscribed_files):
        print(f"[{i+1}/{total_files}] Transcribing {audio_path.stem}...")
        
        # Find corresponding video path for reference
        video_name = audio_path.stem
        possible_video_extensions = [".mp4", ".mkv", ".avi"]
        video_path = None
        
        for ext in possible_video_extensions:
            potential_path = VIDEO_DIR / f"{video_name}{ext}"
            if potential_path.exists():
                video_path = potential_path
                break
        
        # If exact match not found, try to find a video with this name as part of its filename
        if video_path is None:
            for ext in possible_video_extensions:
                matching_files = list(VIDEO_DIR.glob(f"*{video_name}*{ext}"))
                if matching_files:
                    video_path = matching_files[0]
                    break
        
        # Fall back to using the audio file path as reference
        if video_path is None:
            video_path = audio_path
        
        try:
            # Create segments directory if it doesn't exist
            segment_dir = os.path.join(AUDIO_DIR, f"{video_name}_segments")
            os.makedirs(segment_dir, exist_ok=True)
            
            # Check if segments already exist or create them
            segments = []
            existing_segments = list(Path(segment_dir).glob("*.wav"))
            
            if existing_segments:
                # Use existing segments
                sorted_segments = sorted(existing_segments, 
                                        key=lambda x: int(str(x).split('_')[-1].split('.')[0]))
                
                total_duration = 0
                segment_length_ms = 30000  # Default length in ms
                
                for i, segment_path in enumerate(sorted_segments):
                    start_ms = i * segment_length_ms
                    
                    try:
                        audio_segment = AudioSegment.from_file(segment_path)
                        duration_ms = len(audio_segment)
                    except:
                        duration_ms = segment_length_ms
                        
                    end_ms = start_ms + duration_ms
                    total_duration += duration_ms
                    
                    segments.append({
                        'path': str(segment_path),
                        'start_ms': start_ms,
                        'end_ms': end_ms,
                        'duration_ms': duration_ms
                    })
                    
                print(f"  Using {len(segments)} existing segments from {segment_dir}")
                
            else:
                # Create new segments
                print(f"  Segmenting audio file {audio_path}")
                try:
                    # Load audio file
                    audio = AudioSegment.from_file(audio_path)
                    
                    # Calculate number of segments
                    segment_length_ms = 30000
                    audio_length_ms = len(audio)
                    num_segments = audio_length_ms // segment_length_ms + (1 if audio_length_ms % segment_length_ms > 0 else 0)
                    
                    # Split audio into segments
                    for i in range(num_segments):
                        start_ms = i * segment_length_ms
                        end_ms = min((i + 1) * segment_length_ms, audio_length_ms)
                        
                        segment = audio[start_ms:end_ms]
                        segment_path = os.path.join(segment_dir, f"{video_name}_segment_{i:03d}.wav")
                        
                        segment.export(segment_path, format="wav")
                        segments.append({
                            "path": segment_path,
                            "start_ms": start_ms,
                            "end_ms": end_ms,
                            "duration_ms": end_ms - start_ms
                        })
                    
                    print(f"  Audio segmented into {len(segments)} parts")
                    
                except Exception as e:
                    print(f"  Error segmenting audio: {e}")
                    continue
            
            # Transcribe each segment
            full_transcript = []
            
            for i, segment in enumerate(segments):
                print(f"  Transcribing segment {i+1}/{len(segments)}...")
                
                try:
                    # Perform transcription
                    result = whisper_model(
                        segment["path"],
                        return_timestamps=True,
                        generate_kwargs={"language": "en"}
                    )
                    
                    # Calculate absolute timestamps
                    segment_start_sec = segment["start_ms"] / 1000
                    
                    # Process chunk results
                    if "chunks" in result:
                        for chunk in result["chunks"]:
                            # Adjust timestamps to be relative to the full video
                            start_time = segment_start_sec + chunk["timestamp"][0] if chunk["timestamp"][0] is not None else segment_start_sec
                            end_time = segment_start_sec + chunk["timestamp"][1] if chunk["timestamp"][1] is not None else None
                            
                            full_transcript.append({
                                "text": chunk["text"],
                                "start_time": start_time,
                                "end_time": end_time
                            })
                    else:
                        # If no chunks, use the whole segment
                        full_transcript.append({
                            "text": result["text"],
                            "start_time": segment_start_sec,
                            "end_time": segment_start_sec + (segment["duration_ms"] / 1000)
                        })
                        
                except Exception as e:
                    print(f"    ✗ Error transcribing segment {i+1}: {e}")
                    # Continue with other segments even if one fails
            
            # Save the transcript
            os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
            transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{video_name}_transcript.json")
            
            transcript_result = {
                "video_name": video_name,
                "video_path": str(video_path),
                "duration_seconds": (segments[-1]["end_ms"] / 1000) if segments else 0,
                "transcript": full_transcript,
                "transcript_text": " ".join([item["text"] for item in full_transcript]),
            }
            
            with open(transcript_path, 'w') as f:
                json.dump(transcript_result, f, indent=2)
            
            success_count += 1
            results.append({
                "audio": str(audio_path),
                "transcript": str(transcript_path),
                "word_count": len(transcript_result["transcript_text"].split()),
                "status": "success"
            })
            print(f"  ✓ Successfully transcribed {audio_path.name} ({len(full_transcript)} segments)")
                
        except Exception as e:
            print(f"  ✗ Error transcribing {audio_path.name}: {e}")
            results.append({
                "audio": str(audio_path),
                "status": "error",
                "error": str(e)
            })
    
    print(f"\nTranscription complete! Successfully processed {success_count}/{total_files} files.")
    
    # Save transcription log
    log_path = PROCESSED_DIR / "continued_transcription_log.json"
    log_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": total_files,
        "success_count": success_count,
        "results": results
    }
    
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    
    print(f"Log saved to {log_path}")
    return log_data

if __name__ == "__main__":
    print("Loading Whisper model for transcription...")
    whisper_model = load_whisper_model(model_id="openai/whisper-small")

    if whisper_model is not None:
        print("Starting continued transcription...")
        transcription_results = continue_transcription(whisper_model=whisper_model)
    else:
        print("Failed to load Whisper model. Please check your environment configuration.")