def read_file(filepath) -> str:
    with open(filepath) as file:
        return file.read()