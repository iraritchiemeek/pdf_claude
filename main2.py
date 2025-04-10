import asyncio
from io import BytesIO
from pathlib import Path
from typing import Literal
import PyPDF2
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic import BaseModel
from pydantic_ai.usage import UsageLimits
import argparse
from dotenv import load_dotenv

load_dotenv()

model = AnthropicModel('claude-3-5-sonnet-latest')

class PublicationDetail(BaseModel):
  publication_name: Literal['activist', 'transport worker', 'national conference', 'other']
  date: str
  headline: str

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
  file_path = ctx.deps
  print(f"Processing: {file_path}")
  
  with open(file_path, "rb") as f:
    pdf_reader = PyPDF2.PdfReader(f)
    
    if len(pdf_reader.pages) > 0:
      text_content = pdf_reader.pages[0].extract_text()
      print(len(text_content))
      
      if not text_content or len(text_content) < 10:
        return "PDF appears to be image-based or has limited text content. Consider using OCR for better results."
      
      return text_content
    else:
      return "PDF has no pages"


async def main():
  parser = argparse.ArgumentParser(description='Process PDF files and extract information using Claude')
  parser.add_argument('--count', type=int, default=None, help='Number of PDFs to process')
  parser.add_argument('--offset', type=int, default=0, help='Number of PDFs to skip')
  args = parser.parse_args()
  
  pdf_dir = Path("pdfs")
  
  if not pdf_dir.exists() or not pdf_dir.is_dir():
      print(f"Error: The directory {pdf_dir} doesn't exist")
      return
  
  pdf_files = sorted(list(pdf_dir.glob("*.pdf")))
  
  if not pdf_files:
      print(f"No PDF files found in {pdf_dir}")
      return
  
  pdf_files = pdf_files[args.offset:]
  
  if args.count is not None:
      pdf_files = pdf_files[:args.count]
  
  successful = 0
  failed = 0
  
  for pdf_path in pdf_files:
      try:
        result = await agent.run(
          'Process this PDF',
          deps=str(pdf_path),
          usage_limits=UsageLimits(response_tokens_limit=300, request_limit=2, request_tokens_limit=5000),
        )
        print(f"Result for {pdf_path.name}:")
        print(result.data)
        print(result.usage())
        successful += 1
      except Exception as e:
        import sys
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)
        filename, line_number, func_name, text = tb[-1]
        print(f"Failed to process {pdf_path.name}: {e} (at line {line_number} in {func_name})")
        traceback.print_exc()
        failed += 1
  
  print(f"Processing complete. Successful: {successful}, Failed: {failed}")

asyncio.run(main())