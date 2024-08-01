# MD to PDF with Pandoc

This project contains a Python script to recursively combine multiple Markdown (`.md`) files into a single Markdown file, replace links to sections within the combined file, replace image paths, and finally convert the combined Markdown file to a PDF using Pandoc. The script also includes an optional threading mechanism for running the PDF conversion in the background and automatically cleans up the temporary combined Markdown file after the PDF is generated.

## Requirements

Make sure you have the following installed:

- Python 3.x
- Pandoc

To install Pandoc, follow the instructions [here](https://pandoc.org/installing.html).

## Installation

1. **Clone the repository**:

    Clone the repository where you have the Markdown files to be converted to PDF.

    ```sh
    git clone https://github.com/kaldun-tech/buggy-to-bulletproof.git
    ```

2. **Install the required Python packages**:

    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. **PandocMdToPDF - script**:

    ```sh
    git clone https://github.com/kaldun-tech/md-to-pdf.git
    cd md-to-pdf/pandoc
    ```

2. **Run the script**:

    Execute the script to combine Markdown files and convert to PDF. You can choose to run the PDF conversion in the background using threading or in the main thread.

    ```sh
    python PandocMdToPDF.py <directory> <pdf_file>
    ```

    Replace `<directory>` with the path to the directory containing the Markdown files and `<pdf_file>` with the desired output PDF file name. For example:

    ```sh
    python PandocMdToPDF.py ../../buggy-to-bulletproof output.pdf
    ```

### Running with Optional Threading

By default, the script runs the PDF conversion in a separate thread. To control this behavior, modify the `use_threading` parameter in the `PandocMdToPDF.py` script.

- **To run PDF conversion in a separate thread** (default behavior):

    ```python
    combiner.run(use_threading=True)
    ```

- **To run PDF conversion in the main thread**:

    ```python
    combiner.run(use_threading=False)
    ```

### Script Details

The `PandocMdToPDF.py` script performs the following steps:

1. **Collect Markdown Files**: Recursively collects all Markdown files from the specified directory.
2. **Create Section Mapping**: Creates a mapping from file paths to section IDs based on the headings in each file.
3. **Combine Files and Replace Links**: Combines all Markdown files into one, replaces image paths, and updates links to point to the appropriate sections. (You may have to add necessary paths here to avoid asset linking issues simialr to images taken care in the script now)
4. **Convert to PDF**: Uses Pandoc to convert the combined Markdown file to a PDF. This step can optionally be run in a separate thread.
5. **Cleanup**: Automatically removes the combined Markdown file after the PDF is generated.

## License

TODO