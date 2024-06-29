# This is a python script which will read all the "md" files in the given directory

program run in below steps:
1. Identify all md files from the "directory" specified in configuration json
2. Copy all images from the "directory" and store in static folder for Flask to use it from the htmls
3. Grip will be converting md file to html and will keep this html appended to a string
4. Full html for the all md files will open in Flask and then convert the html into pdf
5. Full PDF for all md files (e-book) will be saved into the filname "ouput_file" specified in configuration json

# There is a configuration JSON available with script which has the configurations for the script.

# The configuration have fileds for styles, header , footer templets , parent directoty and other enviormental values.

# Have default value for all configuration expect grip_user and grip_pass (This is nothing but a valid github credentils). 

# below are the configuration parameters and sample values,

    1. footer_template : for footers style of the pdf with page number etc
    "footer_template": "<div style=\"width: 100%; text-align: center; font-size: 10px; padding: 10px 0;\">Page <span class=\"pageNumber\"></span> of <span class=\"totalPages\"></span></div",
    
    2. header_template: header style
    "header_template": "<div style=\"width: 100%; text-align: center; font-size: 10px; padding: 10px 0;\"></div>",

    3. directory: directory location where the github repo is cloned to your system
    "directory": "/home/kaldun/kaldun_tech/small_doc",

    4. first_page_content: first header page contents
    "first_page_content": "<div>From Buggy to Bulletproof</div><div>How to Build Better Software with Test-Driven Development</div><div>By Taras Smereka</div>",

    5. html_cont_first: just for htmls to start (dont change this unless you have to change the margin, font soze etc)
    "html_cont_first": "<!DOCTYPE html><html lang=\"en\"><head></head><body><div style=\"display:flex;align-items: center;flex-direction: column;justify-content: center;margin-top: 60%;font-size: x-large;font-weight: 700;\" class=\"new-page\"> ",

    6. html_cont_last: closure tag for the html (please do not change)
    "html_cont_last": "</div></body></html>",

    7. grip_user: your GitHub user name
    "grip_user":"",

    8. grip_pass: your GitHub password
    "grip_pass":"",

    9. grip_local: host name part of grip url
    "grip_local":"http://localhost:",

    10. grip_port: grip port to run flask server from grip
    "grip_port":"6419",

    11. title_class: title class style name
    "title_class":"Box-title",

    12. chapter_common_substring: common string for all chapters
    "chapter_common_substring":["Chapter", "From Buggy To Bulletproof"],

    13. title_page_text_for_break_down: we will use this to identify the next chapter when it is combined with all md files (please change this if different in your md file)
    "title_page_text_for_break_down":"Title Page",

    14. title_page_id_for_page_break_down: for identifying page brak (please change if it is different in your md file)
    "title_page_id_for_page_break_down": "user-content-table-of-contents",

    15. body_style: body style
    "body_style": "margin-left:50px;margin-right:50px;font-family: sans-serif;",

    16. html_style: hmtl styles
    "html_style": "@page { margin-top: 50px;margin-bottom: 50px; border: 1px solid black; \n header { position: fixed;top: 0;left: 0;right: 0;height: 50px;background-color: #ccc;text-align: center;line-height: 50px;} \n footer {position: fixed;bottom: 0;left: 0;right: 0;height: 50px;background-color: #ccc;text-align: center;line-height: 50px;}} \n .new-page { page-break-after: always;} \n .markdown-break { page-break-before: always;} p { text-align: justify; } li {margin-bottom: 5px}",

    17. markDown_heading_class: header style class
    "markDown_heading_class":"markdown-heading",

    18. pageBreak_class: page break class
    "pageBreak_class" : "markdown-break",

    19. new_page_class: new page style class
    "new_page_class" : "new-page",

    20. ouput_file: output file where to save generated PDF file.
    "ouput_file": "converted_document.pdf",

    21. flask_end_point: flask app url iniitial part
    "flask_end_point": "http://localhost:",

    22. flask_port: flask port to use
    "flask_port":"5000"

    23. image_dest: location to store all images from the repo folder, flask will use this folder to get the images for the htmls and later use in pdfs.
    "image_dest":"static",


# please make sure the parent README file on root folder

# all other md files in different folders to keep in sorted order to maintain the chapeters/sections in correct order

# steps to run
1. install dependencies
    pip install -r requirements.txt

2. set the repo folder name, output file name etc in configuration.json file
3. run md_to_pdf.py program
    python md_to_pdf.py 
    # please make sure you have python3.7 or above installed and python is pointing to the same. if you have both python2 or multiple versions for python3, then run with specific python command
    eg: python3.8 md_to_pdf.py

# setup script to run as GitHub actions

    Example Workflow to Run a Python Script
    Create a .github/workflows directory in your GitHub repository if it doesn't already exist.

    Add a workflow file (e.g., run_python_script.yml) in the .github/workflows directory.

    Define the workflow in the YAML file. Here is an example that runs a Python script named md_to_pdf.py:

    '''
    name: Run Python Script

    # Trigger the workflow on push events to the main branch
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
    '''

    Workflow Explanation
    ----------------------

    name: The name of the workflow.

    on: The event that triggers the workflow. In this case, it runs on push events to the main branch.

    jobs: A collection of jobs that will run in the workflow.

    run-script: A job named run-script.

    runs-on: Specifies the type of machine to run the job on, here it uses the latest version of Ubuntu.

    steps: A series of steps to be executed in the job.

    Checkout repository: Uses the actions/checkout@v2 action to check out the code from the repository.

    Set up Python: Uses the actions/setup-python@v2 action to set up Python 3.8.

    Install dependencies: Installs the dependencies listed in requirements.txt if it exists.

    Run Python script: Runs the Python script md_to_pdf.py.

