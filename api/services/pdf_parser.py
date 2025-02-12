import fitz
from pathlib import Path
import logging
import time
from typing import List, Optional, Union
from docling_core.types.doc import DoclingDocument

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.pdf_splitter import PdfSplitter
from utils.regions import PDFTextRegion, PDFImageRegion
from utils.docling_parser import DoclingParserNoOcr
from utils.helper import get_text_in_bbox
from utils.logging import setup_logging
from utils.translate import translate_markdown

logger = setup_logging(log_level=logging.INFO)

class PdfParser:
    """
    Parses a PDF file and extracts its content into structured regions and markdown format.
    """

    def __init__(self, path: str) -> None:
        """
        Initializes the parser with the given file path.

        Args:
            path (str): Path to the PDF file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        self.file_path = path
        if not Path(path).exists():
            logger.error(f"File {self.file_path} does not exist.")
            raise FileNotFoundError(f"File {self.file_path} does not exist.")

        self.pymupdf_doc = self._get_full_pymupdf_doc()
        self.docling_doc = self._get_full_docling_doc()
        self.regions = self._get_regions()

    def _get_regions(self) -> List[Union[PDFTextRegion, PDFImageRegion]]:
        """
        Splits the PDF into regions based on text and image content.

        Returns:
            List[Region]: List of regions with adjusted bounding boxes.
        """
        start_time = time.time()
        splitter = PdfSplitter(self.pymupdf_doc, self.docling_doc, text_padding=5)
        regions = splitter.split(self.file_path)
        for region in regions:
            page_height = self.docling_doc.pages[region.page_no].size.height
            region.bbox = region.bbox.to_bottom_left_origin(page_height=page_height)
        duration = time.time() - start_time
        logger.info(f"Splitted {self.file_path} into {len(regions)} regions in {duration:.2f} seconds")
        return regions

    def _get_full_docling_doc(self) -> DoclingDocument:
        """
        Parses the PDF file's structure using Docling as well as replaces text components content based on PyMuPDF.

        Returns:
            DoclingDocument: Parsed Docling document.
        """
        start_time = time.time()
        parser = DoclingParserNoOcr()
        result = parser.parse(self.file_path)
        for text_element in result.texts:
            prov = text_element.prov[0]
            page_no = prov.page_no
            page_height = result.pages[page_no].size.height

            top_left_bbox = prov.bbox.to_top_left_origin(page_height).as_tuple()
            text_element.text = get_text_in_bbox(self.pymupdf_doc, page_no - 1, top_left_bbox)

        for table_element in result.tables:
            prov = table_element.prov[0]
            page_no = prov.page_no
            page_height = result.pages[page_no].size.height

            for cell in table_element.data.table_cells:
                if cell.bbox is not None:
                    cell_bbox_top_left = cell.bbox.to_top_left_origin(page_height)
                    x0, y0, x1, y1 = cell_bbox_top_left.as_tuple()
                    cell_padding = 2
                    cell_bbox_with_padding = (x0 - cell_padding, y0 - cell_padding, x1 + cell_padding, y1 + cell_padding)
                    cell.text = get_text_in_bbox(self.pymupdf_doc, page_no - 1, cell_bbox_with_padding)
        duration = time.time() - start_time
        logger.info(f"Parsed {self.file_path} file's text structure with Docling in {duration:.2f} seconds")
        return result

    def _get_full_pymupdf_doc(self) -> fitz.Document:
        """
        Loads the PDF file using PyMuPDF.

        Returns:
            fitz.Document: Loaded PyMuPDF document.

        Raises:
            Exception: If the file cannot be parsed with PyMuPDF.
        """
        try:
            start_time = time.time()
            doc = fitz.open(self.file_path)
            duration = time.time() - start_time
            logger.info(f"Parsed {self.file_path} file's content with PyMuPDF in {duration:.2f} seconds")
            return doc
        except Exception as e:
            logger.exception(f"Unable to parse {self.file_path} with PyMuPDF. {e}")
            raise

    def to_markdown(self, save_as: Optional[str] = None, translate_to_english:bool = False) -> str:
        """
        Converts the parsed PDF regions into markdown format.

        Args:
            save_as (Optional[str]): File path to save the markdown output. Defaults to None.

        Returns:
            str: Markdown representation of the PDF content.
        """
        start_time = time.time()
        md = ''

        for region in self.regions:
            md += '\n' + region.to_markdown(save_dir=Path(save_as).parent if save_as else None)

        duration = time.time() - start_time
        logger.info(f"Converted {self.file_path} into markdown in {duration:.2f} seconds")

        if translate_to_english:
            start_time = time.time()
            md = translate_markdown(md)
            duration = time.time() - start_time
            logger.info(f"Translated all nepali text in parsed markdown in {duration:.2f} seconds")
        
        try:
            if save_as:
                with open(save_as, 'w') as f:
                    f.write(md)
        except Exception as e:
            logger.exception(f"Unable to save parsed markdown as {save_as} : {e}")
        return md