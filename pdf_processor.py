import os
import pdfplumber
import pdf2image
from utils import PopplerUtils, FileUtils
from config import POPPLER_PATH

class PDFProcessor:
    def __init__(self):
        """Initialize the PDF processor and check Poppler installation."""
        PopplerUtils.check_poppler_installation()
        self.script_dir = FileUtils.get_script_dir()

    def process_first_pdf(self):
        """Process the first PDF found in the directory."""
        pdf_files = FileUtils.get_pdf_files(self.script_dir)
        if not pdf_files:
            print("No PDF files found in the directory")
            return False

        pdf_path = os.path.join(self.script_dir, pdf_files[0])
        print(f"Processing {pdf_path}...")
        
        # Extract both text and images
        self.extract_text(pdf_path)
        # self.extract_images(pdf_path) commented out image generation
        return True

    def extract_text(self, pdf_path):
        """Extract text from PDF and save as numbered TXT files."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    text_path = os.path.join(self.script_dir, f"{i+1}.txt")
                    
                    with open(text_path, 'w', encoding='utf-8') as text_file:
                        text_file.write(text)
                    print(f"Saved text to {text_path}")
                    
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")

    def extract_images(self, pdf_path):
        """Convert PDF pages to images and save as numbered JPGs."""
        try:
            images = pdf2image.convert_from_path(
                pdf_path,
                poppler_path=POPPLER_PATH
            )
            
            for i, image in enumerate(images):
                image_path = os.path.join(self.script_dir, f"page_{i+1}.jpg")
                image.save(image_path, "JPEG")
                print(f"Saved image to {image_path}")
                
        except Exception as e:
            print(f"Error converting PDF to images: {str(e)}")

if __name__ == "__main__":
    processor = PDFProcessor()
    processor.process_first_pdf() 