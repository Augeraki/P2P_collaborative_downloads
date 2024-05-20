import os
FRAGMENT_SIZE = 0.5*1024*1024
def partition_file(filename, offset):
    if not os.path.isfile(filename):
        print(f"Error: Input file '{filename}' not found.")
        return
    if not filename.endswith(".txt"):
        print("Only fragment complete files")
        return

    total_size = os.path.getsize(filename)
    num_fragments = int((total_size + offset - 1) / offset)

    with open(filename, 'rb') as input_file:
        directory_path = os.path.dirname(filename)  # Get the directory path of the original file
        for i in range(num_fragments):
            start_pos = i * offset
            end_pos = min((i + 1) * offset, total_size)
            
            input_file.seek(int(start_pos))
            chunk = input_file.read(int(end_pos) - int(start_pos))
            
            fragment_filename = os.path.join(directory_path, f"{os.path.splitext(os.path.basename(filename))[0]}-{i+1}.fragments")
            
            with open(fragment_filename, 'wb') as fragment_file:
                fragment_file.write(chunk)
                
    return num_fragments 
        
def assemble(fragment_directory, num_of_fragments, filename):
    #remake the original file using the fragments
    base_filename = os.path.splitext(os.path.basename(filename))[0] 

    # Initialize an empty bytearray to store the content of the original file
    assembled_content = bytearray()

    # Loop through each fragment file and append its content to the assembled_content
    for i in range(1, num_of_fragments + 1):
        fragment_filename = os.path.join(fragment_directory, f"{base_filename}-{i}.fragments")
        with open(fragment_filename, 'rb') as fragment_file:
            assembled_content.extend(fragment_file.read())

    # Write the assembled content to the output .txt file
    output_filename = os.path.join(fragment_directory, f"{base_filename}.txt")
    with open(output_filename, 'wb') as output_file:
        output_file.write(assembled_content)

def partition_allfiles(directory):
    file_fragments = {}
    files = os.listdir(directory)
    files= [filename for filename in files if filename.endswith(".txt")]
    
    files = [os.path.join(directory, file) for file in files if os.path.isfile(os.path.join(directory, file))]
    for file in files:
        num_frags = partition_file(file, FRAGMENT_SIZE)
        file = os.path.basename(file)
        file_fragments[file] = num_frags
    return file_fragments

#just an idea    
#file_dict = {'file1.txt': {123: ({123, 213}, False), 456: (set(), False), 220: ({123, 213, 1}, True)}}
#if(file_dict['file1.txt'][220][0]== file_dict['file1.txt'][123][0]):
#    pieces = file_dict['file1.txt'][123][0]
#    file_dict['file1.txt'][123] = (pieces, True )
#print(file_dict)

def parse_fragment_dict(s):
    s= s.strip("{")
    s= s.strip("}")
    #list of key value pairs as strings
    pairs = s.split('), ')

    # Initialize an empty dictionary
    result = {}

    # Iterate over key-value pairs
    for pair in pairs:
        token_id , value_str = pair.split(": ({")
        # Convert key to integer
        token_id = int(token_id.strip())

        # Parse value
       
        value_parts = value_str.split("},")
        frag_list = value_parts[0].split(", ")
        frag_list = [frag.strip("'") for frag in frag_list]
        value_bool = bool(value_parts[1].strip())
        value_set = set(frag_list)
        # Add key-value pair to dictionary
        result[token_id] = (value_set, value_bool)
    
    return result

