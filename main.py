import anthropic
import base64
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO
import json
import re
import os
import argparse
from pathlib import Path

load_dotenv()

def extract_json(text):
    pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    json_match = re.search(pattern, text, re.DOTALL)
    
    if json_match:
        return json_match.group(1)
    
    bracket_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
    bracket_match = re.search(bracket_pattern, text, re.DOTALL)
    
    if bracket_match:
        return bracket_match.group(1)
    
    return None

def process_pdf(pdf_path, client):
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

    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
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
Please analyze this document (filename: {pdf_path.name}) and extract the following information:

1. The publication name (select one):
   - activist
   - transport worker
   - national conference
   - other

2. The date (format as mm/yyyy or yyyy)

3. The headline

Consider both the document content and filename when determining the information.

Respond only with valid JSON using this format:
{{
  "publication": "string (one of the categories listed above)",
  "date": "string (in mm/yyyy or yyyy format)",
  "headline": "string"
}}
"""
                    }
                ]
            }
        ],
    )

    response_content = message.content
    txt_filename = pdf_path.with_suffix('.txt')

    if isinstance(response_content, list):
        text_content = ""
        for item in response_content:
            if hasattr(item, 'text'):
                text_content += item.text
        response_content = text_content

    json_str = extract_json(response_content)
    if json_str:
        try:
            parsed_json = json.loads(json_str)
            with open(txt_filename, 'w') as txt_file:
                json.dump(parsed_json, txt_file, indent=2)
            print(f"Successfully created {txt_filename} with the JSON response")
            return True
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print("Extracted content:", json_str)
    else:
        print("Could not extract JSON from the response")
        print("Response content:", response_content)
    
    return False

def main():
    parser = argparse.ArgumentParser(description='Process PDF files and extract information using Claude')
    parser.add_argument('--count', type=int, default=None, help='Number of PDFs to process')
    parser.add_argument('--offset', type=int, default=0, help='Number of PDFs to skip')
    args = parser.parse_args()
    
    client = anthropic.Anthropic()
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
        result = process_pdf(pdf_path, client)
        if result:
            successful += 1
        else:
            failed += 1
    
    print(f"Processing complete. Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main()
