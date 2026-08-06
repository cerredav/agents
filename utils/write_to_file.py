def write_to_file(file, message: str, end_block: bool = False) -> None:
    file.write(message)
    if end_block:
        file.write("\n" + "-"*80 + "\n")
    file.flush()

