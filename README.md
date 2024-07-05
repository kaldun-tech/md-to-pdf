# MD to PDF Converter

This Python script converts all Markdown (`.md`) files in a given directory to a single PDF document.

## How it Works

The program follows these steps:

1. Identifies all `.md` files in the specified directory from the configuration JSON.
2. Copies all images from the directory and stores them in the `static` folder for Flask to use in the HTML files.
3. Converts each `.md` file to HTML using the `grip` library and appends the HTML content to a string.
4. Opens the combined HTML content in a Flask server and converts it to a PDF file.
5. Saves the PDF file with the name specified in the configuration JSON.

## Configuration

The script uses a configuration JSON file to customize various settings. Here are the available configuration parameters and their descriptions:

- `footer_template`: Footer template for the PDF, including page numbers.
- `header_template`: Header template for the PDF.
- `directory`: Directory location where the GitHub repository is cloned.
- `first_page_content`: Content for the first page of the PDF.
- `html_cont_first`: Opening HTML tags for the combined HTML content.
- `html_cont_last`: Closing HTML tags for the combined HTML content.
- `grip_local`: Hostname part of the `grip` URL.
- `grip_port`: Port number for the `grip` Flask server.
- `title_class`: CSS class for titles.
- `chapter_common_substring`: Common substrings for chapter titles.
- `title_page_text_for_break_down`: Text to identify the next chapter when combining files.
- `title_page_id_for_page_break_down`: HTML ID for page breaks.
- `body_style`: CSS styles for the body element.
- `html_style`: CSS styles for the HTML content.
- `markDown_heading_class`: CSS class for Markdown headings.
- `pageBreak_class`: CSS class for page breaks.
- `new_page_class`: CSS class for new pages.
- `ouput_file`: Output filename for the generated PDF.
- `flask_end_point`: Initial part of the Flask app URL.
- `flask_port`: Port number for the Flask app.
- `image_dest`: Directory to store images for Flask to use in the HTML files.

## Prerequisites

- Python 3.7 or later
- Install the required dependencies by running `pip install -r requirements.txt`

## Usage

1. Set the repository folder name, output file name, and other configurations in the `configuration.json` file.
2. Run the `md_to_pdf.py` script: python md_to_pdf.py


If you have multiple Python versions installed, use the specific Python command (e.g., `python3.8 md_to_pdf.py`).

## GitHub Actions Setup

To run the script as a GitHub Action, create a `.github/workflows/run_python_script.yml` file with the following content:

```yaml
name: Run Python Script

on:
  push:
    branches:
      - main

jobs:
  run-script:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

    - name: Run Python script
      run: python md_to_pdf.py
```

This workflow will run the md_to_pdf.py script on every push to the main branch.

## Notes
- Ensure that the parent README file is in the root folder.
- Place all other .md files in different folders to maintain the correct order of chapters/sections.
