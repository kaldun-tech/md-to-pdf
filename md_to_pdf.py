'''Converts Markdown (.md) to PDF format'''

import asyncio
import glob
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import argparse
from tqdm import tqdm

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request
from pyppeteer import launch
from werkzeug.serving import make_server
import logging
import argparse

app = Flask(__name__)
logger = logging.getLogger(__name__)

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
    combined_html = app.config['COMBINED_HTML']
    soup = BeautifulSoup(combined_html, 'html.parser')
    img_tags = soup.find_all('img')

    for img in img_tags:
        src = img['src']
        if not src.startswith(('http://', 'https://', '//')):
            img['src'] = "{{ url_for('static', filename='" + os.path.basename(src) + "') }}"

    body_tag = soup.find('body')
    body_tag['style'] = app.config['root_configuration']['body_style']

    style_tag = soup.find('style')

    if style_tag:
        style_tag.string += "\n " + app.config['root_configuration']['html_style']
    else:
        new_style_tag = soup.new_tag('style')
        new_style_tag.string = app.config['root_configuration']['html_style']
        soup.head.append(new_style_tag)

    markdown_heading_class = app.config['root_configuration']['markDown_heading_class']
    title_page_id_for_page_break_down = app.config['root_configuration']['title_page_id_for_page_break_down']
    title_page_text_for_break_down = app.config['root_configuration']['title_page_text_for_break_down'] 
    page_break_class = app.config['root_configuration']['pageBreak_class']
    markdown_headings = soup.find_all('div', class_=markdown_heading_class)

    for heading in markdown_headings:
        titles = heading.find_all('h1', string=lambda text: text and (title_page_text_for_break_down in text ))
        if heading.find(id=title_page_id_for_page_break_down) or 0 < len(titles):
            heading['class'] = heading.get('class', []) + [page_break_class]

    combined_html = str(soup)
    return render_template_string(combined_html)


class FlaskServer(threading.Thread):
    '''Defines the Flask server'''
    def __init__(self, flask_app, combined_html, host='0.0.0.0', port=5000, root_config=None):
        threading.Thread.__init__(self)
        self.flask_app = flask_app
        self.flask_app.config['COMBINED_HTML'] = combined_html
        self.flask_app.config['root_configuration'] = root_config
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        '''Starts the Flask server'''
        self.server = make_server(self.host, self.port, self.flask_app)
        self.server.serve_forever()

    def stop(self):
        '''Stops the Flask server'''
        if self.server:
            self.server.shutdown()
            self.server = None


def read_config(config_file):
    '''Reads and returns the configuration from the json file'''
    with open(config_file, 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
    return config


def save_custom_config(root_config, directory, output_pdf, grip_user, grip_pass):
    '''Customizes the configuration with command-line inputs'''
    root_config['directory'] = directory
    root_config['output_pdf'] = output_pdf
    root_config['grip_user'] = grip_user
    root_config['grip_pass'] = grip_pass
    return root_config


def find_md_files(directory):
    '''Reads and returns all the MarkDown (md) files'''
    md_files = []
    logging.info("Finding markdown files from the folder %s", directory)
    for root, _, files in tqdm(os.walk(directory)):
        for next_file in files:
            if next_file.endswith('.md'):
                md_files.append(os.path.join(root, next_file))
    md_files.sort()
    logging.info("Found %d markdown files", len(md_files))
    return md_files


def read_md_files(root_config):
    '''Reads the MD files for given configuration'''
    directory = root_config['directory']
    return find_md_files(directory)


def render_markdown_to_html(markdown_file, root_config):
    '''Converts the markdown file to html. Each MD file is treated as a new page'''
    logging.info("Converting markdown file %s to html", markdown_file)
    html_content = ''
    with open('output.log', 'w', encoding='utf-8') as out_log:
        # Redirect stdout and stderr to file
        grip_args = ['grip', markdown_file, '--user',
                root_config["grip_user"], '--pass', root_config['grip_pass']]
        try:
            subprocess.run(grip_args, stdout=out_log, stderr=out_log, check=True, timeout=30)
        except subprocess.CalledProcessError as e:
            logging.error("grip command failed with return code %s", e.returncode)
        except subprocess.TimeoutExpired:
            logging.error("grip command timed out")

    grip_local_url = root_config['grip_local'] + root_config['grip_port']
    html_content = requests.get(grip_local_url, timeout = 30).text

    html_content = disable_links(html_content, root_config)
    html_content = remove_title(html_content, root_config)
    soup = BeautifulSoup(html_content, 'html.parser')
    body_tag = soup.find('body')
    html_content = soup.new_tag('div')
    html_content['id']= os.path.basename(markdown_file).split('.')[0].split('-')[0]
    html_content['class'] = html_content.get('class', []) + [root_config['new_page_class']]

    for child in body_tag.children:
        html_content.append(child if child.name else str(child))

    return html_content


def generate_combined_html(markdown_files, root_config):
    '''Generates the combined HTML for markdown files and given config'''
    logging.info("Generating combined HTML")
    first_page_content = root_config['first_page_content']
    combined_html = ''
    combined_html += root_config['html_cont_first']
    combined_html += first_page_content
    soup_parent = BeautifulSoup(combined_html, 'html.parser')
    parent_body = soup_parent.find("body")

    for markdown_file in markdown_files:
        parent_body.append(render_markdown_to_html(markdown_file, root_config))

    return str(soup_parent)


def disable_links(converted_html, root_config):
    '''Disable all links in the converted HTML file for given config'''
    logging.info("Disabling links in converted HTML")
    soup = BeautifulSoup(converted_html, 'html.parser')
    for a_tag in soup.find_all('a'):
        del a_tag['href']  # Remove the href attribute
    chapter_links = soup.find_all('a', string=lambda text: text and (
        any(substring in text for substring in root_config['chapter_common_substring'])
    ))
    i = 0
    for link in chapter_links:
        # This logic needs to be adjusted based on the read me structure.
        link['href'] = '#ch0' + str(i)
        i += 1
    return str(soup)


def remove_title(converted_html, root_config):
    '''Removes duplicate page titles from converted HTML for given config'''
    logging.info("Removing duplicate page titles from converted HTML")
    soup = BeautifulSoup(converted_html, 'html.parser')
    title_tag = soup.find('title')
    if title_tag:
        title_tag.decompose()
    h2_tags = soup.find_all('h2', class_=root_config['title_class'])

    for tag in h2_tags:
        tag.decompose()
    return str(soup)


def copy_images(root_config):
    '''Copy all image files to configured directory'''
    # Create target directory if it does not exist
    directory = root_config['directory']
    logging.info("Copying images to static folder from the folder %s", directory)
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
                logging.info("Copied: %s", img_path)
            except PermissionError as e:
                logging.error("Permission error copying %s: %s", img_path, e)
            except FileNotFoundError as e:
                logging.error("File not found error copying %s: %s", img_path, e)
            except shutil.Error as e:
                logging.error("Error copying %s: %s", img_path, e)
            except OSError as e:
                logging.error("OS error copying %s: %s", img_path, e)


def start_server(root_config, combined_html):
    '''Starts the Flask server'''
    flask_server = FlaskServer(app, combined_html, host=root_config['flask_host'],
                               port=root_config['flask_port'], root_config=root_config)
    flask_server.start()
    return flask_server


async def save_page_as_pdf(root_config):
    '''Saves the final html content to pdf'''
    output_pdf_path = root_config['output_pdf']
    logging.info("Aggregating md htmls to single PDF file %s", output_pdf_path)

    if os.path.exists(output_pdf_path):
        user_prompt = f"{output_pdf_path} already exists. Do you want to overwrite it? (yes/no): "
        user_choice = input(user_prompt).strip().lower()
        if user_choice == 'no':
            output_pdf_path = input("Enter a new file name for the pdf: ").strip()

    footer_template = root_config['footer_template']
    pbar = tqdm(total=5, desc="Processing", unit="step")

    header_template = root_config['header_template']
    try:
        # TODO Is this done better using pdfkit?
        browser = await launch(headless=True)
        pbar.update(1)
        page = await browser.newPage()
        pbar.update(1)
        flask_url = root_config['flask_end_point'] + root_config['flask_port']
        await page.goto(flask_url, {'waitUntil': 'networkidle2'})
        pbar.update(1)
        pdf_dict = {'path': output_pdf_path, 'format': 'A4', 'displayHeaderFooter': True,
                    'footerTemplate': footer_template,'headerTemplate': header_template}
        await page.pdf(pdf_dict)
        pbar.update(1)
        await browser.close()
        pbar.update(1)
        logging.info("Page saved as PDF to %s", output_pdf_path)
        return True
    except (TimeoutError, ConnectionError) as e:
        # Implement retry logic or log the error
        logging.error("An error occurred: %s", e)
        return False
    except ValueError as e:
        # Log the error and provide a meaningful error message
        logging.error("Invalid input or configuration: %s", e)
        return False
    except PermissionError as e:
        # Log the error and provide a meaningful error message
        logging.error("Permission error: %s", e)
        return False
    except MemoryError as e:
        # Log the error and provide a meaningful error message
        logging.error("Memory error: %s", e)
        return False


def cleanup(flask_server, exitcode):
    '''Cleans up the process'''
    if flask_server:
        flask_server.stop()
    sys.exit(exitcode)


def create_argparse():
    '''Creates the argument parser'''
    parser = argparse.ArgumentParser(description='Convert Markdown files to PDF')
    parser.add_argument('--config', type=str, help='Path to the configuration file', default='configuration.json')
    parser.add_argument('--directory', help='Directory containing Markdown files',
                        default='/mnt/e/git/buggy-to-bulletproof')
    parser.add_argument('--out', help='Output PDF file path', default='pdf/buggy_to_bulletproof.pdf', dest='output_pdf')
    parser.add_argument('grip_user', help='GitHub user for Grip')
    parser.add_argument('grip_pass', help='GitHub password for Grip')
    return parser


def main():
    '''Main method orchestrates execution of other functions'''
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = create_argparse()
    args = parser.parse_args()

    flask_server = None
    root_config = read_config(args.config)
    root_config = save_custom_config(root_config, args.directory, args.output_pdf, args.grip_user, args.grip_pass)
    markdown_files = find_md_files(root_config['directory'])

    if markdown_files:
        copy_images(root_config)
        combined_html = generate_combined_html(markdown_files, root_config)
        flask_server = start_server(root_config, combined_html)
        asyncio.get_event_loop().run_until_complete(save_page_as_pdf(root_config))
        exitcode = 0
    else:
        logging.error("No Markdown files found.")
        exitcode = 1

    cleanup(flask_server, exitcode)


if __name__ == "__main__":
    main()
