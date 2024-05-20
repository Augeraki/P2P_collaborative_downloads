import os
import random
import string
import concurrent.futures

# Function to generate random characters and write them to file
def generate_and_write_chunk(file, chunk_size):
    random_characters = ''.join(random.choices(string.ascii_letters + string.digits, k=chunk_size))
    file.write(random_characters)

# Set the minimum size for each file (5 MB)
min_file_size_bytes = 5500000  # 5 MB in bytes

# Define the chunk size for each thread
chunk_size = 1000000  # Adjust as needed

# Function to generate random characters and fill the file until it reaches the minimum size
def generate_file(file_path):
    with open(file_path, "w") as file:
        bytes_written = 0
        while bytes_written < min_file_size_bytes:
            # Calculate the number of characters needed to reach the minimum size
            remaining_bytes = min_file_size_bytes - bytes_written
            remaining_chars = remaining_bytes  # Assuming each character is 1 byte

            # Generate random characters
            random_characters = ''.join(random.choices(string.ascii_letters + string.digits, k=min(chunk_size, remaining_chars)))
            file.write(random_characters)
            
            # Update bytes_written
            bytes_written += len(random_characters)

# Create directories named peer1, peer2, ..., peer10
for i in range(1, 11):
    directory_name = f"peer{i}"
    os.makedirs(directory_name, exist_ok=True)  # Create directory if it doesn't exist

    # Create four unique files named file1.txt, file2.txt, ..., file4.txt
    for j in range(1, 5):
        file_name = os.path.join(directory_name, f"file{j+4*(i-1)}.txt")
        generate_file(file_name)

print("Directories and files created successfully.")
