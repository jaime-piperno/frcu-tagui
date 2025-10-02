import os
from dotenv import load_dotenv

class Config:
    """
    Load and store configuration parameters from a .env file.

    This class reads environment variables to provide:
    - Moodle credentials
    - Destination folder for downloads
    - Browser headless mode setting
    - Optional academic years to filter courses

    Attributes
    ----------
    user : str
        Moodle username.
    password : str
        Moodle password.
    dest_folder : str
        Path to the folder where downloaded files will be stored.
    headless : bool
        Whether the browser should run in headless mode.
    years : list[str]
        List of academic years as strings to filter courses.
    """

    def __init__(self):
        """
        Initialize configuration by loading environment variables.

        Raises a warning if the .env file does not exist.
        """

        # Load environment variables from .env file
        load_dotenv()
        if not os.path.exists('.env'):
            print('ERROR: .env file does not exist')
        
        # Read variables from environment
        self.user = os.getenv("USER")
        self.password = os.getenv("PASSWORD")
        self.dest_folder = os.getenv("DEST_FOLDER")
        self.headless = os.getenv("HEADLESS", "False").lower() == "true"
        
        # YEARS is optional; split by comma if provided
        self.years = os.getenv("YEARS", "").split(",") if os.getenv("YEARS") else []
