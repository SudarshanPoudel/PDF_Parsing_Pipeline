from pathlib import Path
from docling_core.types.doc import DoclingDocument
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.document_converter import DocumentConverter, PdfFormatOption

from .helper import get_docling_pipeline_options, detect_language


class DoclingParserNoOcr:
    """Parses PDFs without using OCR."""

    def __init__(self):
        """Initializes the parser with a non-OCR pipeline."""
        pipeline_options = get_docling_pipeline_options(do_ocr=False)

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                ),
            }
        )

    def parse(self, path: str) -> DoclingDocument:
        """
        Parses the given PDF without OCR.

        Args:
            path (str): Path to the PDF file.

        Returns:
            DoclingDocument: Parsed document structure.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: If parsing fails.
        """
        _path = Path(path)
        if not _path.exists():
            raise FileNotFoundError(f"File {path} does not exist.")
        
        try:
            conv_result = self.doc_converter.convert(path)
            return conv_result.document
        except Exception as e:
            raise Exception(f"Unable to parse {path} file with docling (no ocr) {e}")


class DoclingParserOcr:
    """Parses PDFs using OCR."""

    def __init__(self):
        pass

    def parse(self, path: str) -> DoclingDocument:
        """
        Parses the given PDF using OCR.

        Args:
            path (str): Path to the PDF file.

        Returns:
            DoclingDocument: Parsed document structure.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: If parsing fails.
        """
        _path = Path(path)
        if not _path.exists():
            raise FileNotFoundError(f"File {path} does not exist.")
        
        try:
            lang = detect_language(path)
            if lang == 'ne': 
                tess_lang = ['nep']
            elif lang == 'en':  
                tess_lang = ['eng']
            else:
                tess_lang = ['eng', 'nep']
            
            pipeline_options = get_docling_pipeline_options(force_full_page_ocr=True, easyocr_langs=[lang], tess_langs=tess_lang)

            self.doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        backend=PyPdfiumDocumentBackend,
                    ),
                }
            )
        
            conv_result = self.doc_converter.convert(path)
            return conv_result.document
        except Exception as e:
            raise Exception(f"Unable to parse {path} file with docling (ocr) {e}")