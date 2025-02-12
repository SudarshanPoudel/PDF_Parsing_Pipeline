import re
from deep_translator import GoogleTranslator

def contains_nepali_text(text: str) -> bool:
    """
    Checks if the given text contains Nepali (Devanagari script) characters.
    """
    # Unicode range for Devanagari script (covers Nepali text)
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(devanagari_pattern.search(text))

def translate_text_recursive(text: str, eng_to_nep: bool = False, MAX_LENGTH = 2000) -> str:
    """
    Translates text between English and Nepali using Google Translate.
    If the text length exceeds 2000 characters, it splits the text at an appropriate boundary and processes recursively.

    Args:
        text (str): The input text to translate.
        eng_to_nep (bool): Direction of translation. Default is False (Nepali to English).
        max_length (int): Maximum length of each chunks to be translated, longer text will get split and translated
    Returns:
        str: The translated text.
    """

    if (not contains_nepali_text(text)):
        return text

    if len(text) <= MAX_LENGTH:
        # Directly translate if within limit
        return GoogleTranslator(source='en' if eng_to_nep else 'ne', 
                                target='ne' if eng_to_nep else 'en').translate(text) or text


    # Define splitting points in order of preference
    split_preferences = ["\n\n", "।", ".", "\n", " "]
    split_point = -1
    half_length = len(text) // 2

    for delimiter in split_preferences:
        split_point = text.rfind(delimiter, 4*half_length//10, 6*half_length//10)
        if split_point != -1:
            break

    if split_point == -1:  # If no good splitting point is found, split at half length
        split_point = half_length

    # Split the text into two parts
    part1 = text[:split_point + 1].strip()
    part2 = text[split_point + 1:].strip()

    # Translate both parts recursively
    translated_part1 = translate_text_recursive(part1, eng_to_nep, MAX_LENGTH)
    translated_part2 = translate_text_recursive(part2, eng_to_nep, MAX_LENGTH)

    # Combine translated parts
    return translated_part1 + "\n" + translated_part2



def translate_markdown(markdown: str, translate: callable=translate_text_recursive) -> str:
    """
    Translates a Markdown-styled string while preserving its structure.

    Args:
        markdown (str): The Markdown content to translate.
        translate (function): A function that takes a string and returns its translation.

    Returns:
        str: The translated Markdown content.
    """
    # Regex patterns to identify markdown elements
    patterns = {
        "code_blocks": r"```.*?```|`.*?`", 
        "headings": r"^(#+)(\s+.*)$",      
        "links": r"\[(.*?)\]\((.*?)\)",     
        "lists": r"^(\s*[-*+]\s+|\d+\.\s+)(.*)$", 
    }

    def translate_match(match, key):
        if key == "code_blocks":
            return match.group(0) 
        if key == "links":
            text, url = match.groups()
            return f"[{translate(text)}]({url})"
        if key == "headings":
            hashes, text = match.groups()
            return f"{hashes} {translate(text.strip())}"
        if key == "lists":
            prefix, text = match.groups()
            return f"{prefix}{translate(text.strip())}"
        return translate(match.group(0))

    # Translate markdown elements
    for key, pattern in patterns.items():
        markdown = re.sub(pattern, lambda m: translate_match(m, key), markdown, flags=re.MULTILINE)

    # Special handling for tables
    def translate_table_row(row):
        cells = row.split('|')
        translated_cells = [
            f"{cell[:len(cell) - len(cell.lstrip())]}{translate(cell.strip())}{cell[len(cell.rstrip()):]}" 
            if cell.strip() and not cell.strip().startswith('-') 
            else cell 
            for cell in cells
        ]
        return '|'.join(translated_cells)

    def process_table(match):
        lines = match.group(0).splitlines()
        translated_lines = [translate_table_row(line) for line in lines]
        return '\n'.join(translated_lines) + '\n'

    markdown = re.sub(r"(^\|.*\|$)(\n|$)", lambda m: process_table(m), markdown, flags=re.MULTILINE)

    # Translate remaining paragraphs
    def translate_paragraph(match):
        return translate(match.group(0).strip())

    markdown = re.sub(r"^(?![#\-|>`*\d+\.\s+-]).+", translate_paragraph, markdown, flags=re.MULTILINE)

    return markdown