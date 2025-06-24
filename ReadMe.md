# Joplin to Paperless-NGX Exporter

Script to export documents from Joplin to PDFs which can be imported into Paperless-NGX.

The tool looks for links to PDFs or to image files in the 'Markdown + Front Matter' export from Joplin.
It uses the title, modified date and creation date from the front matter in the Markdown file to create a new PDF.
If there are multiple PDFs linked in the Markdown file, multiple new PDFs are created. If multiple images are found they are stored as a single PDF.

__Be cautious! Tool is very rough and not tested!__

## Usage

1. Install requirements in virtual environment
2. Export all notes from Joplin with 'Markdown + Front Matter' option.
3. Use script like this:
    ```shell
    $ python joplin_to_paperless.py -h
    usage: joplin_to_paperless.py [-h] [-v] joplin_export_dir output_dir

    Convert Joplin Markdown exports to PDFs for Paperless-NGX.

    positional arguments:
    joplin_export_dir  The root directory of the Joplin 'Markdown + Front Matter' export.
    output_dir         The directory where the generated PDFs will be saved.

    options:
    -h, --help         show this help message and exit
    -v, --verbose      Enable verbose (debug) logging.
    ```