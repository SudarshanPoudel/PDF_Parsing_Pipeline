"""
Helper Functions:
- get_docling_pipeline_options: Configures Docling pipeline options for OCR, table structure, and accelerator settings.
- map_to_unicode: Maps text to Unicode characters, optionally skipping English words.
- get_text_in_bbox: Extracts text from a bounding box in a PDF and maps it to Unicode if needed.
- detect_language: Returns Language of the image
"""

import torch
import npttf2utf
import os
import fitz
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    TesseractOcrOptions,
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableFormerMode
)
from io import BytesIO  
import pytesseract
from PIL import Image
from langdetect import detect

# Functions implementation
def get_docling_pipeline_options(**kwargs):
    """
    Configures Docling pipeline options for OCR, table structure, and accelerator settings.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = kwargs.get('do_ocr', True)
    pipeline_options.do_table_structure = kwargs.get("do_table_structure", True)
    pipeline_options.table_structure_options.do_cell_matching = kwargs.get("do_cell_matching", True)
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    if pipeline_options.do_ocr:
        pipeline_options.images_scale = kwargs.get("images_scale", 2.0)
        pipeline_options.generate_picture_images = kwargs.get("generate_picture_images", True)
            
        if torch.cuda.is_available() and not kwargs.get('use_tesseract', False):
            pipeline_options.ocr_options = EasyOcrOptions(
                use_gpu=True,
                lang=kwargs.get('easyocr_langs', ['en', 'ne']),
                confidence_threshold=kwargs.get('confidence_threshold', 0.1),
                force_full_page_ocr=True
            )
            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=kwargs.get('num_threads', 4), 
                device=AcceleratorDevice.CUDA
            )
        else:
            pipeline_options.ocr_options = TesseractOcrOptions(
                lang=kwargs.get('tess_langs', ['eng', 'nep']),
                force_full_page_ocr=True
            )
    return pipeline_options


def map_to_unicode(text) -> str:
    """
    Maps text to Unicode characters, optionally skipping English words.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_mapper_path = os.path.join(script_dir, "..", "assets", "font_mapper.json")
    font_mapper_path = os.path.abspath(font_mapper_path)    
    mapper = npttf2utf.FontMapper(map_json=font_mapper_path)
    mapped_text = []
    for word in text.split(" "):
        mapped_word = mapper.map_to_unicode(
            word, 
            unescape_html_input=False, 
            escape_html_output=False
        )
        mapped_text.append(mapped_word)
    
    return " ".join(mapped_text)

def get_text_in_bbox(doc: fitz.Document, page: int, bbox: fitz.Rect) -> str:
    """
    Extracts text from a bounding box in a PDF and maps it to Unicode if needed.
    """
    page_obj = doc[page]
    text_instances = page_obj.get_text("dict", clip=bbox)["blocks"]
    fonts_to_map = []

    script_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_file_path = os.path.join(script_dir, "..", "assets", "nepali_fonts.txt")
    fonts_file_path = os.path.abspath(fonts_file_path)

    with open(fonts_file_path, "r") as f:
        fonts_to_map = f.read().split("\n")
    extracted_text = []
    for block in text_instances:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font = span.get("font", "")
                text = span.get("text", "")
                if font in fonts_to_map:
                    text = map_to_unicode(text)  
                extracted_text.append(text)

    return " ".join(extracted_text)

def detect_language(pdf_path: str) -> str:
    """Detects the majority language of text in a given scanned PDF."""
    doc = fitz.open(pdf_path)
    all_text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        pix = page.get_pixmap() 
        img = pix.tobytes("png")  
        img_pil = Image.open(BytesIO(img))
        text = pytesseract.image_to_string(img_pil, lang='eng+nep')  
        all_text += text
    
    if not all_text:
        return 'en'
    detected_lang = detect(all_text)
    
    return detected_lang