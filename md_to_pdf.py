'''Converts Markdown (.md) to PDF format'''

import asyncio
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from multiprocessing import Process
from threading import Thread
from tqdm import tqdm

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request
from pyppeteer import launch
from werkzeug.serving import make_server

@app.route('/shutdown', methods=['POST'])
def shutdown():
    '''Shuts down flask server'''
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'


@app.route('/')
def index():
    '''Defines index route for Flask'''
    return render_template_string(COMBINED_HTML)


class FlaskServer:
    '''Defines the Flask server'''
    def __init__(self, app, host='0.0.0.0', port=5000):
        self.app = app
        self.host = host
        self.port = port
        self.server = None

    def start(self):
        '''Starts the Flask server'''
        self.server = make_server(self.host, self.port, self.app)
        print(f"Flask app running on http://{self.host}:{self.port}")
        self.server.serve_forever()

    def stop(self):
        '''Stops the Flask server'''
        if self.server:
            self.server.shutdown()
            self.server = None


def disable_links(converted_html):
    '''Disable all links in the converted HTML file'''
    soup = BeautifulSoup(converted_html, 'html.parser')
    for a_tag in soup.find_all('a'):
        del a_tag['href']  # Remove the href attribute
    chapter_links = soup.find_all('a', string=lambda text: text and (any(substring in text for substring in root_config['chapter_common_substring'])))
    i = 0
    for link in chapter_links:
        # This logic needs to be adjusted based on the read me structure.
        link['href'] = '#ch0' + str(i)
        i += 1
    return str(soup)


def remove_title(converted_html):
    '''Removes duplicate page titles from converted HTML'''
    soup = BeautifulSoup(converted_html, 'html.parser')
    title_tag = soup.find('title')
    if title_tag:
        title_tag.decompose()
    h2_tags = soup.find_all('h2', class_=root_config['title_class'])

    for tag in h2_tags:
        tag.decompose()
    return str(soup)


def generate_combined_html(markdown_files, root_config):
    '''Generates the combined HTML for markdown files given a config'''
    combined_html = ''
    for markdown_file in markdown_files:
        combined_html += render_markdown_to_html(markdown_file, root_config)
    return combined_html


def render_markdown_to_html(markdown_file, root_config):
    '''Converts the markdown file to html. Each MD file is treated as a new page'''
    print("Converting markdown file ", markdown_file, " to html")
    html_content = ''
    grip_process = None
    with open('output.log', 'w') as f:
        grip_process = subprocess.Popen(
            ['grip', markdown_file, '--user', root_config["grip_user"], '--pass', root_config['grip_pass']],
            stdout=f,  # Redirect stdout to a file
            stderr=f   # Redirect stderr to the same file
        )

    html_content = requests.get(root_config['grip_local'] + root_config['grip_port'], timeout = 30).text
    grip_process.terminate()

    html_content = disable_links(html_content)
    html_content = remove_title(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    body_tag = soup.find('body')
    html_content = soup.new_tag('div')
    html_content['id']= os.path.basename(markdown_file).split('.')[0].split('-')[0]
    html_content['class'] = html_content.get('class', []) + [root_config['new_page_class']]

    for child in body_tag.children:
        html_content.append(child if child.name else str(child))

    return html_content


async def save_page_as_pdf(root_config):
    '''Saves the final html content to pdf'''
    output_pdf_path = root_config['output_pdf']
    print(f"Aggregating md htmls to single PDF file {output_pdf_path}")

    if os.path.exists(output_pdf_path):
        user_choice = input(f"{output_pdf_path} already exists. Do you want to overwrite it? (yes/no): ").strip().lower()
        if user_choice == 'no':
            output_pdf_path = input("Enter a new file name for the pdf: ").strip()

    footer_template = root_config['footer_template']
    pbar = tqdm(total=5, desc="Processing", unit="step")

    header_template = root_config['header_template']
    try:
        browser = await launch(headless=True)
        pbar.update(1)
        page = await browser.newPage()
        pbar.update(1)
        flask_url = root_config['flask_end_point'] + root_config['flask_port']
        await page.goto(flask_url, {'waitUntil': 'networkidle2'})
        pbar.update(1)
        await page.pdf({ 'path': output_pdf_path, 'format': 'A4', 'displayHeaderFooter': True,'footerTemplate': footer_template,'headerTemplate': header_template})
        pbar.update(1)
        await browser.close()
        pbar.update(1)
        print(f"Page saved as PDF to {output_pdf_path}")
        return True
    except (TimeoutError) as e:
        # Implement retry logic or log the error
        print(f"An error occurred: {e}")
        return False
    except ValueError as e:
        # Log the error and provide a meaningful error message
        print(f"Invalid input or configuration: {e}")
        return False
    except PermissionError as e:
        # Log the error and provide a meaningful error message
        print(f"Permission error: {e}")
        return False
    except MemoryError as e:
        # Log the error and provide a meaningful error message
        print(f"Memory error: {e}")
        return False
    except Exception as e:
        # Catch any other unexpected exceptions
        print(f"An unexpected error occurred: {e}")
        return False


def copy_images(root_config):
    '''Copy all image files to a directory'''
    # Create target directory if it does not exist
    directory = root_config['directory']
    print("Copying images to static folder from the folder ", directory)
    if not os.path.exists(root_config['image_dest']):
        os.makedirs(root_config['image_dest'])

    # Define the patterns for image files
    image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.tiff"]

    # Iterate over all the image patterns
    for pattern in image_patterns:
        # Use glob to find all matching files recursively
        for img_path in tqdm(glob.iglob(os.path.join(directory, '**', pattern), recursive=True)):
            # Copy each image to the target directory
            try:
                shutil.copy(img_path, root_config['image_dest'])
                print(f"Copied: {img_path}")
            except PermissionError as e:
                print(f"Permission error copying {img_path}: {e}")
            except FileNotFoundError as e:
                print(f"File not found error copying {img_path}: {e}")
            except OSError as e:
                print(f"OS error copying {img_path}: {e}")
            except shutil.Error as e:
                print(f"Error copying {img_path}: {e}")


def find_md_files(directory):
    '''Read all the MD files into memory'''
    md_files = []
    print("Finding markdown files from the folder ", directory)
    for root, dirs, files in tqdm(os.walk(directory)):
        for next_file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, next_file))
    md_files.sort()
    return md_files


def read_config():
    '''Reads the configuration from the json file'''
    with open('configuration.json', 'r') as config_file:
        config = json.load(config_file)
    return config


def read_md_files(root_config):
    '''Reads the MD files for given configuration'''
    directory = root_config['directory']
    return find_md_files(directory)


def start_server(root_config):
    '''Starts the Flask server'''
    app = Flask(__name__)
    flask_server = FlaskServer(app, host=root_config['flask_host'], port=root_config['flask_port'])
    flask_server.start()
    return flask_server

def cleanup(flask_server, exitcode):
    '''Cleans up the process'''
    flask_server.stop()
    sys.exit(exitcode)

# Global variable to store the combined_html
COMBINED_HTML = ''

def main():
    '''Main method'''
    root_config = read_config()
    directory = root_config['directory']
    markdown_files = find_md_files(directory)

    if markdown_files:
        print(f"Markdown files found: {len(markdown_files)}")
        copy_images(root_config)
        combined_html = generate_combined_html(markdown_files, root_config)
        global COMBINED_HTML
        COMBINED_HTML = combined_html
        flask_server = start_server(root_config)
        asyncio.get_event_loop().run_until_complete(save_page_as_pdf(root_config))
        exitcode = 0
    else:
        print("ERROR: No Markdown files found.")
        exitcode = 1

    cleanup(flask_server, exitcode)


if __name__ == "__main__":
    main()
