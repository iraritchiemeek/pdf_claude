# PDF Information Extractor

This tool uses Claude AI to analyze PDF documents and extract key information such as publication type, date, and headline.

## Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install requirements:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Create a `.env` file with your Anthropic API key:
     ```
     ANTHROPIC_API_KEY=your_api_key_here
     ```

## Usage

1. Add your PDF files to the `/pdfs` directory

2. Run the script:

   ```bash
   python main.py
   ```

3. Optional parameters:

   - `--offset n`: Skip the first n PDF files
   - `--count n`: Process only n PDF files

   Example:

   ```bash
   python main.py --offset 5 --count 10
   ```

The script will create a corresponding .txt file for each processed PDF containing the extracted information in JSON format.
