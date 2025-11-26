def run_full_huggingface_pipeline():
    """Run the complete lecture notes generation pipeline using only Hugging Face models"""
    print("Starting full lecture notes generation pipeline with Hugging Face models")
    print("=" * 80)
    
    # 0. Set up Hugging Face access
    print("\n0. Setting up Hugging Face access...")
    hf_setup = setup_huggingface()
    if not hf_setup:
        print("Failed to set up Hugging Face access. Cannot proceed.")
        return {"error": "Hugging Face setup failed"}
    
    # 1. Check system capabilities
    print("\n1. Checking system capabilities...")
    system_info = check_environment()
    
    # 2. Process videos for audio extraction
    print("\n2. Processing videos for audio extraction...")
    processing_results = process_all_videos(extract_audio=True, segment_audio=True)
    
    # 3. Transcribe audio files
    print("\n3. Transcribing audio files...")
    whisper_model = load_whisper_model()
    transcription_results = batch_transcribe_audio_files(whisper_model=whisper_model)
    
    # 4. Extract slide content
    print("\n4. Processing slides...")
    slide_files = list(SLIDES_DIR.glob("*.pptx")) + list(SLIDES_DIR.glob("*.ppt")) + list(SLIDES_DIR.glob("*.pdf"))
    print(f"Found {len(slide_files)} slide files")
    
    slide_processing_results = batch_process_slides()
    
    # 5. Generate lecture notes using Hugging Face models
    print("\n5. Generating lecture notes with Hugging Face models...")
    notes_generation_results = batch_generate_lecture_notes_huggingface()
    
    print("\n=== Pipeline Execution Complete ===\n")
    print(f"Processed {processing_results.get('extract_audio', {}).get('total_videos', 0)} videos")
    print(f"Generated {notes_generation_results.get('success_count', 0)} lecture notes")
    print(f"Output files can be found in {NOTES_DIR}")
    
    return {
        "system_info": system_info,
        "processing_results": processing_results,
        "transcription_results": transcription_results,
        "slide_processing_results": slide_processing_results,
        "notes_generation_results": notes_generation_results
    }

# Uncomment to run the full pipeline with Hugging Face models
# full_pipeline_results = run_full_huggingface_pipeline()