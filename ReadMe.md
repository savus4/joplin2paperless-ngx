# Joplin to Paperless-NGX Exporter

Tool has two parts: 
* Script to preprocess exported documents from Joplin to PDFs which can be imported into Paperless-NGX.
* Script which uploads the PDFs using the paperless-ngx API to set the original creation date.

__Be cautious! Tool is very rough and not tested!__

## Preprocessing Script

The script looks for links to PDFs or to image files in the 'Markdown + Front Matter' export from Joplin.
It uses the title, modified date and creation date from the front matter in the Markdown file to create a new PDF.
If there are multiple PDFs linked in the Markdown file, multiple new PDFs are created. If multiple images are found they are stored as a single PDF.

### Usage

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

## Uploading PDFs to Paperless-NGX

The script `upload_to_paperless.py` uploads all PDFs from a specified folder to your Paperless-NGX instance using its API. It sets the document's creation date in Paperless-NGX to match the file's creation date as shown in macOS Finder (using `st_birthtime` if available). Should work for other operating systems as well, but not tested.

### Requirements
1. Install requirements in virtual environment (same as for first script)
2. Create a `.env` file in your project root with (see `examples.env`):
    ```env
    PAPERLESS_API_URL=http://localhost:8000
    PAPERLESS_API_TOKEN=your_token_here
    ```

### Usage

```shell
$ python upload_to_paperless.py -h
usage: upload_to_paperless.py [-h] [--api-url API_URL] [--api-token API_TOKEN]
                              --pdf-folder PDF_FOLDER [--no-verify-ssl] [--verbose]

Upload PDFs to Paperless-ngx with correct dates.

options:
  -h, --help            show this help message and exit
  --api-url API_URL     Paperless-ngx API base URL, is read from .env file as default (e.g.
                        http://localhost:8000)
  --api-token API_TOKEN
                        Paperless-ngx API token, is read from .env file as default
  --pdf-folder PDF_FOLDER
                        Folder containing PDFs to upload
  --no-verify-ssl       Disable SSL verification (not recommended)
  --verbose             Enable debug logging
```

