import anthropic
import base64
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO
import json
import os
import argparse
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel
from pydantic_ai import Agent

load_dotenv()

class Publication(BaseModel):
    publication: Literal["activist", "transport worker", "national conference", "other"]
    date: str  # in mm/yyyy or yyyy format
    headline: str

class DocumentAnalyzer(Agent):
    def analyze_document(self, filename: str, pdf_data: str) -> Publication:
        """
        Analyze a PDF document and extract publication information.
        
        Args:
            filename: The name of the PDF file
            pdf_data: Base64-encoded PDF data
            
        Returns:
            Publication object containing publication type, date, and headline
        """
        return self.model(
            user=[
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data
                    }
                },
                {
                    "type": "text",
                    "text": f"""
Please analyze this document (filename: {filename}) and extract the following information:

1. The publication name (select one):
   - activist
   - transport worker
   - national conference
   - other

2. The date (format as mm/yyyy or yyyy)

3. The headline

Consider both the document content and filename when determining the information.
"""
                }
            ]
        )

def process_pdf(pdf_path, analyzer):
    print(f"Processing: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_reader = PyPDF2.PdfReader(f)
        
        pdf_writer = PyPDF2.PdfWriter()
        
        if len(pdf_reader.pages) > 0:
            pdf_writer.add_page(pdf_reader.pages[0])
        
        first_page_bytes = BytesIO()
        pdf_writer.write(first_page_bytes)
        first_page_bytes.seek(0)
        
        pdf_data = base64.standard_b64encode(first_page_bytes.read()).decode("utf-8")

    try:
        # Use the analyzer to extract structured information
        result = analyzer.analyze_document(pdf_path.name, pdf_data)
        
        # Save the result to a text file
        txt_filename = pdf_path.with_suffix('.txt')
        with open(txt_filename, 'w') as txt_file:
            json.dump(result.model_dump(), txt_file, indent=2)
        
        print(f"Successfully created {txt_filename} with the JSON response")
        return True
    
    except Exception as e:
        print(f"Error analyzing document: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Process PDF files and extract information using Claude with PydanticAI')
    parser.add_argument('--count', type=int, default=None, help='Number of PDFs to process')
    parser.add_argument('--offset', type=int, default=0, help='Number of PDFs to skip')
    parser.add_argument('--model', type=str, default="claude-3-7-sonnet-20250219", help='Model to use for analysis')
    args = parser.parse_args()
    
    # Create the document analyzer agent
    analyzer = DocumentAnalyzer(
        model_name=args.model,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    pdf_dir = Path("pdfs")
    
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        print(f"Error: The directory {pdf_dir} doesn't exist")
        return
    
    pdf_files = sorted(list(pdf_dir.glob("*.pdf")))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    # Apply offset
    pdf_files = pdf_files[args.offset:]
    
    # Apply count limit if specified
    if args.count is not None:
        pdf_files = pdf_files[:args.count]
    
    successful = 0
    failed = 0
    
    for pdf_path in pdf_files:
        result = process_pdf(pdf_path, analyzer)
        if result:
            successful += 1
        else:
            failed += 1
    
    print(f"Processing complete. Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main()
