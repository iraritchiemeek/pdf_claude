import asyncio
from typing import Annotated
import json
import sys
import traceback
from pathlib import Path
from typing import List, Literal, Optional
import re

import PyPDF2
import argparse
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.usage import UsageLimits

# Load environment variables
load_dotenv()

# Define the data model for publication details
class PublicationDetail(BaseModel):
    publication_name: Literal['activist', 'transport worker', 'national conference', 'other']
    date: Annotated[str, Field(description='The date of the publication in MM/YYYY or YYYY format.')]
    headline: Annotated[str, Field(description='The headline of the publication. It should not be all capital letters.')]

# Initialize the AI model
model = AnthropicModel('claude-3-5-sonnet-latest')

# Create the agent with the specified configuration
agent = Agent(
    model,
    result_type=PublicationDetail,
    deps_type=str,
    system_prompt=(
        'use the `get_pdf_content` tool to get the PDF content and then extract the publication details'
    ),
)

@agent.tool  
def get_pdf_content(ctx: RunContext[str]) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        ctx: RunContext containing the file path as deps
    
    Returns:
        Extracted text content or error message
    """
    file_path = ctx.deps
    print(f"Processing: {file_path}")
    
    try:
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            if len(pdf_reader.pages) == 0:
                return "PDF has no pages"
                
            text_content = pdf_reader.pages[0].extract_text()
            print(f"Extracted {len(text_content)} characters of text")
            
            if not text_content or len(text_content) < 10:
                return "PDF appears to be image-based or has limited text content. Consider using OCR for better results."
            
            return text_content
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

async def process_pdf(pdf_path: Path) -> Optional[PublicationDetail]:
    """
    Process a single PDF file and extract publication details.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        PublicationDetail object or None if processing failed
    """
    try:
        result = await agent.run(
            'Process this PDF',
            deps=str(pdf_path),
            usage_limits=UsageLimits(
                response_tokens_limit=300, 
                request_tokens_limit=5000
            ),
        )
        
        print(f"Result for {pdf_path.name}:")
        print(result.data)
        print(result.usage())
        
        # Save result to txt file
        txt_filename = pdf_path.with_suffix('.txt')
        with open(txt_filename, 'w') as txt_file:
            json.dump({
                "publication": result.data.publication_name,
                "date": result.data.date,
                "headline": result.data.headline
            }, txt_file, indent=2)
        print(f"Successfully created {txt_filename} with the JSON response")
        
        return result.data
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)
        filename, line_number, func_name, text = tb[-1]
        print(f"Failed to process {pdf_path.name}: {e} (at line {line_number} in {func_name})")
        traceback.print_exc()
        return None

def get_pdf_files(directory: Path, offset: int = 0, count: Optional[int] = None) -> List[Path]:
    """
    Get a list of PDF files from the specified directory.
    
    Args:
        directory: Directory to search for PDF files
        offset: Number of files to skip
        count: Maximum number of files to return
    
    Returns:
        List of Path objects for PDF files
    """
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory {directory} doesn't exist")
    
    pdf_files = sorted(list(directory.glob("*.pdf")))
    
    if not pdf_files:
        print(f"No PDF files found in {directory}")
        return []
    
    # Apply offset and count
    pdf_files = pdf_files[offset:]
    if count is not None:
        pdf_files = pdf_files[:count]
        
    return pdf_files

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process PDF files and extract information using Claude')
    parser.add_argument('--count', type=int, default=None, help='Number of PDFs to process')
    parser.add_argument('--offset', type=int, default=0, help='Number of PDFs to skip')
    parser.add_argument('--dir', type=str, default="pdfs", help='Directory containing PDF files')
    args = parser.parse_args()
    
    # Get PDF files to process
    pdf_dir = Path(args.dir)
    try:
        pdf_files = get_pdf_files(pdf_dir, args.offset, args.count)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    successful = 0
    failed = 0
    
    # Process each PDF file
    for pdf_path in pdf_files:
        result = await process_pdf(pdf_path)
        if result:
            successful += 1
        else:
            failed += 1
    
    print(f"Processing complete. Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())