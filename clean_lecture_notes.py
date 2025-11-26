import os
import re

def clean_lecture_notes(input_file_path, output_file_path=None):
    """
    Removes all thinking parts (enclosed in <think> and </think> tags) from lecture notes.
    
    Parameters:
    input_file_path (str): Path to the input lecture notes file
    output_file_path (str, optional): Path to save the cleaned lecture notes.
                                     If None, will use the input filename with '_clean' suffix.
    
    Returns:
    str: Path to the cleaned lecture notes file
    """
    try:
        # Read the input file
        with open(input_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Remove standalone <think> and </think> lines
        content = re.sub(r'^# <think>\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^### <think>\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^</think>\s*$', '', content, flags=re.MULTILINE)
        
        # Remove all content between <think> and </think> tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # Remove any remaining <think> or </think> tags
        content = content.replace('<think>', '').replace('</think>', '')
        
        # Clean up excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Create output file path if not provided
        if output_file_path is None:
            base_name, extension = os.path.splitext(input_file_path)
            output_file_path = f"{base_name}_clean{extension}"
        
        # Write the cleaned content to the output file
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        return output_file_path
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def process_directory(input_dir, output_dir=None):
    """
    Process all .txt files in the specified directory to remove thinking parts.
    
    Parameters:
    input_dir (str): Directory containing lecture note files
    output_dir (str, optional): Directory to save cleaned files. If None, uses input_dir.
    
    Returns:
    list: List of processed file paths
    """
    if output_dir is None:
        output_dir = input_dir
    
    os.makedirs(output_dir, exist_ok=True)
    
    processed_files = []
    for filename in os.listdir(input_dir):
        if filename.endswith('.txt'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename.replace('.txt', '_clean.txt'))
            result = clean_lecture_notes(input_path, output_path)
            if result:
                processed_files.append(result)
                print(f"Processed: {input_path} -> {output_path}")
    
    return processed_files

if __name__ == '__main__':
    # Example usage for a single file
    # input_path = '/Users/koushikmithul/Documents/sem6/LLM/Hackathon/data/output/lecture_notes/Expn_-_tree_notes.txt'
    # output_path = clean_lecture_notes(input_path)
    # if output_path:
    #     print(f"Successfully cleaned lecture notes: {output_path}")
    
    # Uncomment to process all files in the lecture_notes directory
    input_dir = '/Users/koushikmithul/Documents/sem6/LLM/Hackathon/data/output/lecture_notes'
    output_dir = '/Users/koushikmithul/Documents/sem6/LLM/Hackathon/data/output/lecture_notes/clean'
    processed_files = process_directory(input_dir, output_dir)
    print(f"Processed {len(processed_files)} files")