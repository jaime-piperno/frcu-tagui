import requests
import re
import os

class ResourceDownloader:
    """
    Handles downloading resources (PDF files) from Moodle courses and sections.

    This class manages cookies, destination folders, file naming, and downloading
    PDF files using the `requests` library.

    Attributes
    ----------
    session : requests.Session
        Requests session initialized with Moodle cookies.
    course_name : str
        Sanitized course name used for folder creation.
    section_name : str
        Sanitized section name used for folder creation.
    dest_folder : str
        Root folder where files will be stored.
    """
    
    def __init__(self, cookies, dest_folder, course_name, section_name):
        """
        Initialize the ResourceDownloader.

        Parameters
        ----------
        cookies : list[dict]
            Cookies obtained from the Selenium session to maintain authentication.
        dest_folder : str
            Root folder where downloaded files will be stored.
        course_name : str
            Name of the course (used to create subfolder).
        section_name : str
            Name of the section (used to create subfolder).
        """

        self.session = requests.Session()

        self.course_name = self.sanitize_name(course_name)
        self.section_name = self.sanitize_name(section_name)
        self.dest_folder = os.path.join(dest_folder, self.course_name)

        self.create_dest_folder(self.dest_folder)
        self.load_cookies(cookies)

    def load_cookies(self, cookies):
        """
        Load cookies into the requests session for authentication.

        Parameters
        ----------
        cookies : list[dict]
            List of cookies, each with 'name' and 'value'.
        """

        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
    
    def create_dest_folder(self, path):
        """
        Create a folder if it does not exist.

        Parameters
        ----------
        path : str
            Path of the folder to create.
        """

        if not os.path.exists(path):
            os.makedirs(path)

    def sanitize_name(self, name):
        """
        Sanitize a string to make it safe for Windows filenames/folder names.

        Replaces characters not allowed in filenames with underscores and limits
        the length to 50 characters.

        Parameters
        ----------
        name : str
            Original name string.

        Returns
        -------
        str
            Sanitized name string.
        """

        return re.sub(r'[<>:"/\\|?*]', '_', name[:50])

    def short_path(self, path, max_length=254):
        """
        Ensure the full file path does not exceed the Windows maximum allowed length.

        Parameters
        ----------
        path : str
            Original file path.
        max_length : int, optional
            Maximum allowed length for the path (default: 254, Windows maximum).

        Returns
        -------
        str
            Shortened path if needed.
        """

        if len(path) > max_length:
            actual_len = len(path)
            excess_len = actual_len - max_length
            path = path[:-excess_len]+ ".pdf"
        return path

    def download_pdf(self, url, filename):
        """
        Download a PDF file from a given URL and save it in the correct folder.

        Handles folder creation, file naming, path length, and skips files
        that already exist.

        Parameters
        ----------
        url : str
            URL of the PDF file to download.
        filename : str
            Desired filename for the downloaded PDF (without extension).
        """

        path = os.path.join(self.dest_folder, self.section_name)
        self.create_dest_folder(path)

        filename = self.sanitize_name(filename) + ".pdf"
        
        path = os.path.join(path, filename)
        # Ensure the path length is within system limits
        path = self.short_path(path)

        # Skip downloading if file already exists
        if os.path.exists(path):
            print(f"File already exists: {filename}")
            return

        # Make HTTP GET request to download the PDF
        r = self.session.get(url, stream=True)

        if r.status_code == 200:
            with open(path, 'wb') as f:
                # Write file in chunks to avoid memory issues with large PDFs
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
        else:
            # Print error if download fails
            print(f"Failed to download {filename}. Status code: {r.status_code}")
