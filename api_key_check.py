def load_api_key(filepath):
    """
    Load the API key from a given filepath.

    :param filepath: The path to the file containing the API key.
    :return: The API key as a string if found and not empty.
    :raises: FileNotFoundError, ValueError if the key is not found or is empty.
    """
    try:
        with open(filepath, "r") as f:
            api_key = f.read().strip()
        
        if not api_key:
            raise ValueError("API key is empty!")
  
        return api_key

    except FileNotFoundError:
        print(f"Error: {filepath} file not found. Please ensure you have the API key stored in this file.")
        exit(1)
    except ValueError as ve:
        print(f"Error: {ve}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        exit(1)
