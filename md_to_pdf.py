import subprocess
import requests
import time
import os
from bs4 import BeautifulSoup
import asyncio
from pyppeteer import launch
from flask import Flask, render_template_string, request
import threading
import json
import shutil
import glob
from tqdm import tqdm
import sys
from threading import Thread
import socket
from multiprocessing import Process
from werkzeug.serving import make_server


# Read configurations from  the json file
json_file_path = 'configuration.json'
with open(json_file_path, 'r') as file:
    root_config = json.load(file)

# Create flask endpoint to render final converted html TODO what is this for?
html_content = ''
# TODO is this redundant?
app = Flask(__name__)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    '''Shuts down flask server'''
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

def check_port_in_use(port):
    '''Checks whether port is in use'''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
    except socket.error as e:
        if e.errno == 98:  # Port is already in use
            return True
    finally:
        s.close()
    return False


@app.route('/')
def index():
    '''Defines index route for Flask'''
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img')

    for img in img_tags:
        src = img['src']
        if not src.startswith(('http://', 'https://', '//')):
            img['src'] = "{{ url_for('static', filename='" + os.path.basename(src) + "') }}"

    body_tag = soup.find('body')
    body_tag['style'] = root_config['body_style']

    style_tag = soup.find('style')

    if style_tag:
        style_tag.string += "\n " + root_config['html_style']
    else:
        new_style_tag = soup.new_tag('style')
        new_style_tag.string = root_config['html_style']
        soup.head.append(new_style_tag)

    markdown_headings = soup.find_all('div', class_=root_config['markDown_heading_class'])

    for heading in markdown_headings:
        titles = heading.find_all('h1', string=lambda text: text and (root_config['title_page_text_for_break_down'] in text ))
        if heading.find(id=root_config['title_page_id_for_page_break_down']) or len(titles) > 0:
            heading['class'] = heading.get('class', []) + [root_config['pageBreak_class']]

    modified_html = str(soup)
    return render_template_string(modified_html)

port = int(root_config['flask_port'])

def run_flask_app():
    '''Runs flask app'''
    # Check if port is already in use
    global server
    # App routes defined here
    server = ServerThread(app)
    server.start()

class ServerThread(threading.Thread):
    '''Thread for running Flask server'''

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('0.0.0.0', port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        '''Runs flask server'''
        self.server.serve_forever()

    def shutdown(self):
        '''Shuts down flask server'''
        self.server.shutdown()

def start_server():
    '''Starts server thread'''
    global server
    # TODO is this redundant?
    flask_app = Flask('md_to_pdf')
    # App routes defined here
    server = ServerThread(flask_app)
    server.start()

def stop_server():
    '''Stops server thread'''
    global server
    server.shutdown()

#start_server()
if check_port_in_use(port):
    print(f"Port {port} is already in use. Exiting script.")
    sys.exit(0)

flask_thread = threading.Thread(target=run_flask_app)
flask_thread.start()


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


def render_markdown_to_html(markdown_file):
    '''Converts the markdown file to html. Each MD file is treated as a new page'''
    print("Converting markdown file ", markdown_file, " to html")
    #grip_process = subprocess.Popen(['grip', markdown_file , '--user', root_config["grip_user"], '--pass', root_config['grip_pass']])
    grip_process = None
    with open('output.log', 'w') as f:
        grip_process = subprocess.Popen(
            ['grip', markdown_file, '--user', root_config["grip_user"], '--pass', root_config['grip_pass']],
            stdout=f,  # Redirect stdout to a file
            stderr=f   # Redirect stderr to the same file
        )
        #grip_process.wait()  # Wait for the process to complete

    time.sleep(10)
    html_content = requests.get(root_config['grip_local']+root_config['grip_port']).text
    grip_process.terminate()

    html_content = disable_links(html_content)
    html_content = remove_title(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    body_tag = soup.find('body')
    new_div = soup.new_tag('div')
    new_div['id']= os.path.basename(markdown_file).split('.')[0].split('-')[0]
    new_div['class'] = new_div.get('class', []) + [root_config['new_page_class']]

    for child in body_tag.children:
        new_div.append(child if child.name else str(child))

    return new_div


async def save_page_as_pdf(url, output_pdf_path):
    '''Saves the final html content to pdf'''
    print(f"Converting md htmls to single PDF file {output_pdf_path}")

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
        await page.goto(url, {'waitUntil': 'networkidle2'})
        pbar.update(1)
        await page.pdf({ 'path': output_pdf_path, 'format': 'A4', 'displayHeaderFooter': True,'footerTemplate': footer_template,'headerTemplate': header_template})
        pbar.update(1)
        await browser.close()
        pbar.update(1)
        print(f"Page saved as PDF to {output_pdf_path}")
        stop_server()
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")


def copy_images():
    '''Copy all image files to a directory'''
    # Create target directory if it does not exist
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
            except Exception as e:
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

# Main

directory = root_config['directory']  # Replace with your directory path
markdown_files = find_md_files(directory)
copy_images()


if 0 < len(markdown_files):
    print("Markdown files found: ", len(markdown_files))
    outPutPdf = []
    firstPageContent = root_config['first_page_content']
    html_cont = root_config['html_cont_first'] + firstPageContent + root_config['html_cont_last']
    soupParent = BeautifulSoup(html_cont, 'html.parser')
    parentBody = soupParent.find("body")

    for file in tqdm(markdown_files):
        print("Processing file:",file)
        html = render_markdown_to_html(file)
        parentBody.append(html)

    # Delete the output.log file after the process completes
    if os.path.exists("output.log"):
        os.remove("output.log")
    # TODO what is this?
    html_content = str(soupParent)
    asyncio.get_event_loop().run_until_complete(save_page_as_pdf(root_config['flask_end_point']+root_config['flask_port'], root_config['ouput_file']))
else:
    print("No Markdown files found and program now exit!")
    print("Press Ctrl+C to exit!")       
    sys.exit(0)
