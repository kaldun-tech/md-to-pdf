'''Converts Markdown (.md) to PDF format with Pandoc'''
import os
import re
import subprocess
import threading
import argparse

class PandocMdToPDF:
    """
    class PandocMdToPDF
    """
    def __init__(self, directory, o_file, pdf_file):
        """
        Class constructor

        Parameters:
        directory (str): The directory string of the repo location.
        o_file (str): The temp file name to save the combined md file.
        pdf_file (str): The filename to store PDF file.
        
        Returns:
        Class: Instance of the PandocMdToPDF class.
        """
        self.directory = directory
        self.output_file = o_file
        self.pdf_file = pdf_file
        self.markdown_files = []
        self.section_mapping = {}

    def create_slug(self, text):
        """
        Create a URL-friendly slug from a given text.
        
        Parameters:
        text (str): The text to convert into a slug.
        
        Returns:
        str: The slugified version of the text.
        """
        return re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()

    def collect_markdown_files(self):
        """
        Collect all Markdown files recursively from the specified directory.
        """
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.md'):
                    self.markdown_files.append(os.path.join(root, file))
        self.markdown_files.sort()

    def create_section_mapping(self):
        """
        Create a mapping from file paths to section IDs based on the headings in each file.
        """
        for file_path in self.markdown_files:
            with open(file_path, 'r') as infile:
                for line in infile:
                    if line.startswith('#'):
                        heading = line.strip('#').strip()
                        section_id = self.create_slug(heading)
                        relative_path = os.path.relpath(file_path, self.directory)
                        if relative_path not in self.section_mapping:
                            self.section_mapping[relative_path] = []
                        self.section_mapping[relative_path].append(f'#{section_id}')
    
    def combine_files_and_replace_links(self):
        """
        Combine all Markdown files into one and replace image paths and links to sections.
        """
        with open(self.output_file, 'w') as outfile:
            for file_path in self.markdown_files:
                with open(file_path, 'r') as infile:
                    content = infile.read()
                    
                    # Replace all instances of /images/ with {directory}/images/
                    # you may also add other asset folders (if any) here to avoid hyperlink issues
                    modified_content = content.replace('/images/', f'{self.directory}/images/')
                    
                    # Replace markdown file links with section links
                    for relative_path, section_ids in self.section_mapping.items():
                        for section_id in section_ids:
                            # Match link patterns and replace them
                            link_pattern = re.compile(rf'\[([^\]]+)\]\({relative_path}\)')
                            modified_content = link_pattern.sub(rf'[\1]({section_id})', modified_content)
                                        
                    outfile.write(modified_content)
                    outfile.write('\n\n\\newpage\n\n')  # Add space and page break between files

    def convert_to_pdf(self):
        """
        Convert the combined Markdown file to a PDF using Pandoc.
        """
        try:
            print("Pandoc is running in the background to generate the PDF...")
            subprocess.run(['pandoc', self.output_file, '-o', self.pdf_file], check=True)
            print("PDF generation completed.")
            self.cleanup()
        except Exception as e:
            self.cleanup()
            print(f"Error while generating PDF: {e}")

    def cleanup(self):
        """
        Remove the combined Markdown file after the PDF is generated.
        """
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
            print(f"Removed temporary file: {self.output_file}")

    def run(self, use_threading=False):
        """
        Run the Markdown combiner process: collect files, create section mappings,
        combine files, and convert the combined Markdown to PDF.
        
        Parameters:
        use_threading (bool): If True, run the PDF conversion in a separate thread.
        """
        try:
            self.collect_markdown_files()
            self.create_section_mapping()
            self.combine_files_and_replace_links()
            
            if use_threading:
                # Run the PDF conversion in a separate thread
                pdf_thread = threading.Thread(target=self.convert_to_pdf)
                pdf_thread.start()
                pdf_thread.join()
            else:
                # Run the PDF conversion in the main thread
                self.convert_to_pdf()
        except Exception as e:
            self.cleanup()
            print(f"Error while generating PDF: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Combine Markdown files and convert to PDF.')
    parser.add_argument('directory', type=str, help='Directory containing the Markdown files')
    parser.add_argument('pdf_file', type=str, help='Output PDF file name')
    
    args = parser.parse_args()
    
    # Output Markdown file
    OUT_FILE = 'combined.md'

    pd_md_to_pdf = PandocMdToPDF(args.directory, OUT_FILE, args.pdf_file)
    pd_md_to_pdf.run(use_threading=True)  # Set to False if you don't want to use threading
