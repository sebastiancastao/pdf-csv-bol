import os
import gc
import pdfplumber
import pdf2image
from utils import PopplerUtils, FileUtils, PopplerNotFoundError
from config import POPPLER_PATH

class PDFProcessor:
    def __init__(self, session_dir):
        """Initialize the PDF processor with a session directory."""
        self.session_dir = session_dir
        self.poppler_available = False
        
        # Check Poppler availability without crashing
        try:
            PopplerUtils.check_poppler_installation()
            self.poppler_available = True
        except PopplerNotFoundError as e:
            print(f"⚠️ Poppler not available: {str(e)}")
            print("📄 PDF processing will use pdfplumber only (text extraction)")
            self.poppler_available = False
        except Exception as e:
            print(f"⚠️ Error checking Poppler: {str(e)}")
            print("📄 PDF processing will use pdfplumber only (text extraction)")
            self.poppler_available = False

    def process_first_pdf(self):
        """Process the first PDF found in the directory."""
        try:
            pdf_files = [f for f in os.listdir(self.session_dir) if f.lower().endswith('.pdf')]
            if not pdf_files:
                print("❌ No PDF files found in the session directory")
                return False

            pdf_path = os.path.join(self.session_dir, pdf_files[0])
            print(f"📄 Processing PDF: {pdf_path}")
        
            # Extract text using pdfplumber (always available)
            success = self.extract_text(pdf_path)
            
            if success:
                print(f"✅ PDF processed successfully: {pdf_files[0]}")
            
                # Clean up the PDF file after processing
                try:
                    os.remove(pdf_path)
                    print(f"🗑️ Removed processed PDF: {pdf_files[0]}")
                except Exception as cleanup_error:
                    print(f"⚠️ Warning: Could not remove PDF file: {str(cleanup_error)}")
            
                # Force garbage collection
                gc.collect()
            
                return True
            else:
                print(f"❌ Failed to extract text from PDF: {pdf_files[0]}")
                return False
            
        except Exception as e:
            print(f"❌ Error processing PDF: {str(e)}")
            return False

    def extract_text(self, pdf_path):
        """Extract text from PDF and save as numbered TXT files."""
        try:
            print(f"📄 Extracting text from PDF: {os.path.basename(pdf_path)}")
            
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    print("❌ PDF has no pages")
                    return False
                
                page_count = len(pdf.pages)
                print(f"📄 Processing {page_count} pages")
                
                for i, page in enumerate(pdf.pages):
                    try:
                        # Process one page at a time
                        text = page.extract_text()
                        
                        if not text or text.strip() == "":
                            print(f"⚠️ Page {i+1} has no extractable text")
                            text = f"[Page {i+1} - No text content found]"
                        
                        text_path = os.path.join(self.session_dir, f"{i+1}.txt")
                    
                        with open(text_path, 'w', encoding='utf-8') as text_file:
                            text_file.write(text)
                        
                        print(f"✅ Saved text from page {i+1} to {os.path.basename(text_path)}")
                    
                        # Clear page from memory
                        if hasattr(page, 'flush_cache'):
                            page.flush_cache()
                    
                        # Force garbage collection every few pages
                        if i % 5 == 0:
                            gc.collect()
                        
                    except Exception as page_error:
                        print(f"⚠️ Error processing page {i+1}: {str(page_error)}")
                        # Continue with other pages
                        continue
                        
            print(f"✅ Text extraction completed for {page_count} pages")
            return True
                    
        except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as err:
            print(f"PDF syntax error → {err}")
            return False
        except Exception as e:
            print(f"❌ Error extracting text from PDF: {str(e)}")
            return False

    def extract_images(self, pdf_path):
        """Convert PDF pages to images and save as numbered JPGs."""
        if not self.poppler_available:
            print("⚠️ Poppler not available - image extraction skipped")
            return False
            
        try:
            print(f"🖼️ Extracting images from PDF: {os.path.basename(pdf_path)}")
            
            images = pdf2image.convert_from_path(
                pdf_path,
                poppler_path=POPPLER_PATH
            )
            
            for i, image in enumerate(images):
                image_path = os.path.join(self.session_dir, f"page_{i+1}.jpg")
                image.save(image_path, "JPEG")
                print(f"✅ Saved image for page {i+1} to {os.path.basename(image_path)}")
                
            print(f"✅ Image extraction completed for {len(images)} pages")
            return True
                
        except Exception as e:
            print(f"❌ Error converting PDF to images: {str(e)}")
            return False

if __name__ == "__main__":
    processor = PDFProcessor(".")  # Use current directory for CLI usage
    processor.process_first_pdf() 