'''Converts Markdown (.md) to PDF format'''

import asyncio
import glob
import json
import os
import shutil
import subprocess
import sys
from tqdm import tqdm

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request
from pyppeteer import launch
from werkzeug.serving import make_server
import threading
import time

app = Flask(__name__)

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

    markdown_headings = soup.find_all('div', class_=app.config['root_configuration']['markDown_heading_class'])

    for heading in markdown_headings:
        titles = heading.find_all('h1', string=lambda text: text and (app.config['root_configuration']['title_page_text_for_break_down'] in text ))
        if heading.find(id=app.config['root_configuration']['title_page_id_for_page_break_down']) or len(titles) > 0:
            heading['class'] = heading.get('class', []) + [app.config['root_configuration']['pageBreak_class']]

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


def read_config():
    '''Reads and returns the configuration from the json file'''
    with open('configuration.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
    return config


def find_md_files(directory):
    '''Reads and returns all the MarkDown (md) files'''
    md_files = []
    print("Finding markdown files from the folder ", directory)
    for root, dirs, files in tqdm(os.walk(directory)):
        for next_file in files:
            if next_file.endswith('.md'):
                md_files.append(os.path.join(root, next_file))
    md_files.sort()
    return md_files


def read_md_files(root_config):
    '''Reads the MD files for given configuration'''
    directory = root_config['directory']
    return find_md_files(directory)


def render_markdown_to_html(markdown_file, root_config):
    '''Converts the markdown file to html. Each MD file is treated as a new page'''
    print("Converting markdown file ", markdown_file, " to html")
    html_content = ''
    grip_process = None
    with open('output.log', 'w', encoding='utf-8') as out_log:
        # Redirect stdout and stderr to file
        grip_args = ['grip', markdown_file, '--user',
                root_config["grip_user"], '--pass', root_config['grip_pass']]
        grip_process = subprocess.Popen(grip_args, stdout=out_log, stderr=out_log)
    time.sleep(10)
    grip_local_url = root_config['grip_local'] + root_config['grip_port']
    html_content = requests.get(grip_local_url, timeout = 30).text
    grip_process.terminate()

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
    firstPageContent = root_config['first_page_content']
    combined_html = ''
    combined_html += root_config['html_cont_first']
    combined_html += firstPageContent
    soupParent = BeautifulSoup(combined_html, 'html.parser')
    parentBody = soupParent.find("body")
    
    #combined_html = ''
    for markdown_file in markdown_files:
        parentBody.append(render_markdown_to_html(markdown_file, root_config))
    return str(soupParent)


def disable_links(converted_html, root_config):
    '''Disable all links in the converted HTML file for given config'''
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
            except shutil.Error as e:
                print(f"Error copying {img_path}: {e}")
            except OSError as e:
                print(f"OS error copying {img_path}: {e}")


def start_server(root_config, combined_html):
    '''Starts the Flask server'''
    flask_server = FlaskServer(app, combined_html, host=root_config['flask_host'], port=root_config['flask_port'], root_config=root_config)
    flask_server.start()
    return flask_server


async def save_page_as_pdf(root_config, combined_html):
    '''Saves the final html content to pdf'''
    output_pdf_path = root_config['output_pdf']
    print(f"Aggregating md htmls to single PDF file {output_pdf_path}")

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
        print(f"Page saved as PDF to {output_pdf_path}")
        return True
    except (TimeoutError, ConnectionError) as e:
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


def cleanup(flask_server, exitcode):
    '''Cleans up the process'''
    if flask_server:
        flask_server.stop()
    sys.exit(exitcode)


def main():
    '''Main method orchestrates execution of other functions'''
    flask_server = None
    root_config = read_config()
    directory = root_config['directory']
    markdown_files = find_md_files(directory)

    if markdown_files:
        print(f"Markdown files found: {len(markdown_files)}")
        copy_images(root_config)
        combined_html = generate_combined_html(markdown_files, root_config)
        
        flask_server = start_server(root_config, combined_html)
        asyncio.get_event_loop().run_until_complete(save_page_as_pdf(root_config, combined_html))
        exitcode = 0
    else:
        print("ERROR: No Markdown files found.")
        exitcode = 1

    cleanup(flask_server, exitcode)


if __name__ == "__main__":
    main()
