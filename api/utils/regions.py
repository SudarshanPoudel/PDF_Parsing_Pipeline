from io import BytesIO
from .docling_parser import DoclingParserOcr
from docling_core.types.doc import ImageRefMode, ImageRef, Size
import fitz
import os
from pathlib import Path
from typing import List


class PDFTextRegion:
    """
    A class representing a text region in a PDF document.
    Extracts text elements from a specified bounding box (bbox) and page.
    """

    def __init__(self, pymupdf_doc: fitz.Document, docling_doc: object, page_no: int, bbox: object):
        """
        Initialize the PDFTextRegion with a PyMuPDF document, Docling document, page number, and bounding box.

        Args:
            pymupdf_doc: The PyMuPDF document object.
            docling_doc: The Docling document object used for parsing.
            page_no: The page number containing the region.
            bbox: The bounding box of the region to extract.
        """
        self.pymupdf_doc = pymupdf_doc
        self.docling_doc = docling_doc
        self.page_no = page_no
        self.bbox = bbox.to_top_left_origin(self.docling_doc.pages[self.page_no].size.height)

    def to_markdown(self, save_dir: str = '') -> str:
        """
        Extracts the elements within the defined region and converts them to Markdown format.

        Args:
            save_dir: The directory to save the Markdown file.

        Returns:
            The Markdown representation of the extracted region.
        """
        self.elements = self._get_region_elements()
        if self.elements:
            children_refs = self._get_all_elements_ref_list()
            start_index = children_refs.index(self.elements[0].get_ref().cref)
            end_index = children_refs.index(self.elements[-1].get_ref().cref) + 1
            md = self.docling_doc.export_to_markdown(from_element=start_index, to_element=end_index+1)
            return md
        else:
            return ''

    def _get_all_elements_ref_list(self) -> List[str]:
        """
        Get all element references in the document.

        Returns:
            A list of element references.
        """
        refs = [elem[0].self_ref for elem in self.docling_doc.iterate_items(with_groups=True, traverse_pictures=True)]
        return refs

    def _get_region_elements(self) -> List[object]:
        """
        Extracts elements within the bounding box of the specified page.

        Returns:
            A list of elements within the bounding box.
        """
        x0, y0, x1, y1 = self.bbox.as_tuple()
        region_elements = []

        for element in self.docling_doc.texts + self.docling_doc.tables:
            prov = element.prov[0]
            if prov.page_no != self.page_no:
                continue  
            ex0, ey0, ex1, ey1 = prov.bbox.as_tuple()
            if ex0 >= x0 and ey0 >= y0 and ex1 <= x1 and ey1 <= y1:
                region_elements.append(element)
        return region_elements


class PDFImageRegion:
    """
    A class representing an image region in a PDF document.
    Extracts images from a specified bounding box (bbox) and page, then converts them to Markdown format.
    """

    def __init__(self, pymupdf_doc: fitz.Document, docling_doc: object, page_no: int, bbox: object):
        """
        Initialize the PDFImageRegion with a PyMuPDF document, Docling document, page number, and bounding box.

        Args:
            pymupdf_doc: The PyMuPDF document object.
            docling_doc: The Docling document object used for parsing.
            page_no: The page number containing the image region.
            bbox: The bounding box of the region to extract.
        """
        self.pymupdf_doc = pymupdf_doc
        self.docling_doc = docling_doc
        self.page_no = page_no
        self.bbox = bbox
        self.image = self._get_image_stream()
        self.parser = DoclingParserOcr()

    def _get_pdf_of_image(self) -> str:
        """
        Extracts the image from the bounding box and saves it as a temporary PDF.

        Args:
            output_pdf: The path to save the extracted image as a PDF.

        Returns:
            The path to the saved PDF containing the extracted image.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        temp_dir = os.path.join(parent_dir, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        output_pdf = os.path.join(temp_dir, 'image_as_pdf_temp.pdf')

        page_obj = self.pymupdf_doc[self.page_no-1]
        page_height = self.docling_doc.pages[self.page_no].size.height
        bbox_top_left = self.bbox.to_top_left_origin(page_height)
        pixmap = page_obj.get_pixmap(clip=fitz.Rect(bbox_top_left.as_tuple()))

        pdf_doc = fitz.open()
        rect = fitz.Rect(0, 0, pixmap.width, pixmap.height)
        pdf_page = pdf_doc.new_page(width=rect.width, height=rect.height)
        pdf_page.insert_image(rect, stream=pixmap.tobytes("png"))
        pdf_doc.save(output_pdf)
        pdf_doc.close()
        return output_pdf

    def _get_image_stream(self) -> BytesIO:
        """
        Extracts the image from the bounding box and returns it as a byte stream.

        Returns:
            A byte stream containing the extracted image.
        """
        page_height = self.docling_doc.pages[self.page_no].size.height
        bbox_top_left = self.bbox.to_top_left_origin(page_height)
        pix = self.pymupdf_doc[self.page_no-1].get_pixmap(clip=fitz.Rect(bbox_top_left.as_tuple()))
        img_bytes = pix.tobytes("png")  
        return BytesIO(img_bytes)

    def to_markdown(self, save_dir: Path = None) -> str:
        """
        Converts the extracted image to Markdown format, saving it as a file if necessary.

        Args:
            save_dir: The directory to save the image and Markdown file.

        Returns:
            The Markdown representation of the extracted image.
        """
        if save_dir is not None:
            image_dir_path = save_dir / f'{self.docling_doc.name}-images'
        else:
            image_dir_path = Path(f'{self.docling_doc.name}-images')

        image_dir_path.mkdir(parents=True, exist_ok=True)
        docling_doc = self.parser.parse(self._get_pdf_of_image()) 

        for i, picture in enumerate(docling_doc.pictures):
            pic_name = f"picture-{self.page_no}_{i}_{int(picture.prov[0].bbox.as_tuple()[0])}_{int(picture.prov[0].bbox.as_tuple()[1])}"
            element_image_filename = (
                image_dir_path / f"{pic_name}.png"
            )
            with element_image_filename.open("wb") as fp:
               picture.get_image(docling_doc).save(fp, "PNG")
            
            size = Size(width=picture.prov[0].bbox.width, height=picture.prov[0].bbox.height)
            picture.image = ImageRef(mimetype='image/png', dpi=300, size=size, uri=Path(f'{self.docling_doc.name}-images/{pic_name}.png'))
        md = docling_doc.export_to_markdown(image_mode=ImageRefMode.REFERENCED, image_placeholder="\n\n<<Image>>\n\n")
        if md == '':
            pic_name = f"picture_{self.page_no}_{int(self.bbox.as_tuple()[0])}_{int(self.bbox.as_tuple()[1])}"
            element_image_filename = (
                image_dir_path / f"{pic_name}.png"
            )
            image_stream = self._get_image_stream()
            with element_image_filename.open('wb') as file:
                file.write(image_stream.getvalue())
            md = f'\n\n![Image]({self.docling_doc.name}-images/{pic_name}.png)'
        
        return md