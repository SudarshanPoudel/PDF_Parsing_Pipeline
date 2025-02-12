import fitz
from typing import List, Union
from .regions import PDFImageRegion, PDFTextRegion
from docling_core.types.doc import BoundingBox, CoordOrigin, DoclingDocument


class PdfSplitter:
    """
    Splits a PDF into structured text and image regions.
    """

    def __init__(self, pymupdf_doc: fitz.Document, docling_doc: DoclingDocument, text_padding: int = 0) -> None:
        """
        Initialize PdfSplitter with documents and padding.

        Args:
            pymupdf_doc (fitz.Document): PyMuPDF document object.
            docling_doc (DoclingDocument): Docling document object.
            text_padding (int): Padding to apply around text regions.
        """
        self.pymupdf_doc = pymupdf_doc
        self.docling_doc = docling_doc
        self.text_padding = text_padding

    def split(self, path: str) -> List[Union[PDFImageRegion, PDFTextRegion]]:
        """
        Extract text and image regions from the PDF.

        Args:
            path (str): Path to the PDF file.

        Returns:
            List[Union[PDFImageRegion, PDFTextRegion]]: All extracted and processed regions.
        """
        document = fitz.open(path)
        content_regions = []

        for page_num in range(len(document)):
            page = document[page_num]
            regions = []

            # Extract text blocks
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                bbox = block[:4]
                regions.append({"type": "text", "bbox": bbox, "page": page_num + 1})

            # Extract images
            image_list = page.get_images(full=True)
            for img in image_list:
                bbox_rect = page.get_image_bbox(img)
                bbox = (bbox_rect.x0, bbox_rect.y0, bbox_rect.x1, bbox_rect.y1)

                # Check if the bbox is valid
                if bbox and bbox != (1.0, 1.0, -1.0, -1.0):
                    regions.append({"type": "image", "bbox": bbox, "page": page_num + 1})

            # Sort regions by their top-left corner for correct order
            regions.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))

            # Merge consecutive regions of the same type and transform them
            merged_regions = self._merge_and_transform(regions)
            content_regions.append(merged_regions)

        all_regions = [reg for page_regions in content_regions for reg in page_regions]
        return all_regions

    def _merge_and_transform(self, regions: List[dict]) -> List[Union[PDFImageRegion, PDFTextRegion]]:
        """
        Merge consecutive regions and convert to appropriate objects.

        Args:
            regions (List[dict]): List of raw regions extracted from the PDF.

        Returns:
            List[Union[PDFImageRegion, PDFTextRegion]]: Merged and transformed regions.
        """
        if not regions:
            return []

        merged = [regions[0]]
        for current in regions[1:]:
            last = merged[-1]
            if current["type"] == last["type"] and current["page"] == last["page"]:
                # Merge bounding boxes
                x0 = min(last["bbox"][0], current["bbox"][0])
                y0 = min(last["bbox"][1], current["bbox"][1])
                x1 = max(last["bbox"][2], current["bbox"][2])
                y1 = max(last["bbox"][3], current["bbox"][3])
                last["bbox"] = (x0, y0, x1, y1)
            else:
                merged.append(current)

        transformed_regions = []
        for region in merged:
            if region["type"] == "text":
                x0, y0, x1, y1 = region["bbox"]
                region["bbox"] = (
                    x0 - self.text_padding,
                    y0 - self.text_padding,
                    x1 + self.text_padding,
                    y1 + self.text_padding,
                )
                r = PDFTextRegion(
                    self.pymupdf_doc,
                    self.docling_doc,
                    region["page"],
                    BoundingBox.from_tuple(region["bbox"], origin=CoordOrigin.TOPLEFT),
                )
            else:
                r = PDFImageRegion(
                    self.pymupdf_doc,
                    self.docling_doc,
                    region["page"],
                    BoundingBox.from_tuple(region["bbox"], origin=CoordOrigin.TOPLEFT),
                )

            transformed_regions.append(r)

        return transformed_regions