from MoodleSession import MoodleSession
from ResourceDownloader import ResourceDownloader
from Config import Config
import pandas as pd
import os

class Main:
    """
    Main class for automating PDF downloads from the virtual campus
    using Selenium. This class handles session initialization, course
    navigation, section parsing, and resource downloading.

    Attributes
    ----------
    user : str
        Username for the virtual campus.
    password : str
        Password for the virtual campus.
    dest_folder : str
        Local directory where files will be downloaded.
    headless : bool
        Whether the browser runs in headless mode.
    years : list[int]
        Academic years to filter when fetching courses.
    no_downloaded : pd.DataFrame
        DataFrame that stores skipped resources (non-PDF).
    session : MoodleSession
        Active Moodle session handler for interacting with the website.
    """

    def __init__(self, config:Config):
        """
        Initialize the main bot with configuration parameters.

        Parameters
        ----------
        config : Config
            Configuration object containing user credentials,
            destination folder, headless mode, and course years.
        """

        self.user = config.user
        self.password = config.password
        self.dest_folder = config.dest_folder
        self.headless = config.headless
        self.years = config.years
        self.no_downloaded = self.get_no_downloaded_csv()
        self.session = MoodleSession(user=self.user, 
                            password=self.password,
                            headless=self.headless)
    
    def get_no_downloaded_csv(self):
        """
        Load or initialize the CSV file containing skipped resources.

        Returns
        -------
        pd.DataFrame
            DataFrame containing resources that could not be downloaded.
        """

        path = os.path.join(self.dest_folder, 'no_downloaded.csv')
        if os.path.exists(path):
            return pd.read_csv(path, encoding='utf-8')

        return pd.DataFrame(columns=["Fecha", "Materia", "Sección", "Archivo"])

    def start_session(self):
        """
        Start the Moodle session and configure the course view
        (number of courses, type, and layout).
        """

        self.session.login("http://campusvirtual.frcu.utn.edu.ar/virtual/my/courses.php")

        self.session.change_num_courses_shown()
        self.session.change_type_courses_shown()
        self.session.change_view_courses_shown()

    def look_courses(self, year=None):
        """
        Navigate through available courses for a given academic year.

        Parameters
        ----------
        year : int, optional
            Academic year to filter courses. If None, fetches all courses.
        """

        courses = self.session.get_course_cards(year)

        for course in courses:
            course.open()
            course.get_name()  

            print(f"Course: {course.name}")

            self.look_sections(course)
        
        # Reset course search state to empty
        self.session.clear_search_courses()

    def look_sections(self, course):
        """
        Explore all sections of a given course and handle their resources.

        Parameters
        ----------
        course : Course
            Course object obtained from the session.
        """

        try:
            sections = course.get_sections()

            for section in sections:
                downloader = ResourceDownloader(cookies=self.session.get_cookies(), dest_folder=self.dest_folder, 
                                    course_name=course.name, section_name=section.name)
                section.open()
                self.handle_files(section, downloader, course_name=course.name)
        except:
            # Catch all errors to avoid crashing the entire process
            print(f"ERROR ON COURSE: {course.name}")
        
        # Go back to the course list
        self.session.driver.back()

    def handle_files(self, section, downloader, course_name):
        """
        Process files in a course section: download PDFs and log skipped files.

        Parameters
        ----------
        section : Section
            Section object containing resources.
        downloader : ResourceDownloader
            Downloader instance to handle file saving.
        course_name : str
            Name of the parent course.
        """
                
        pdfs, others = section.get_resources()

        # Download all PDFs
        for pdf_name, pdf_url in pdfs:
            downloader.download_pdf(url=pdf_url, filename=pdf_name)
        
        # Log other file types
        rows_to_add = []

        for other_name, _ in others:
            rows_to_add.append({
                "Fecha": pd.Timestamp.now(),
                "Materia": course_name,
                "Sección": section.name,
                "Archivo": other_name
            })
            print(f"Skipped (not PDF): {other_name}")

        if rows_to_add:
            df_new = pd.DataFrame(rows_to_add)
            if self.no_downloaded.empty:
                self.no_downloaded = df_new
            else:
                self.no_downloaded = pd.concat(
                    [self.no_downloaded, pd.DataFrame(rows_to_add)],
                    ignore_index=True
                )

    def main(self):
        """
        Run the bot workflow:
        - Start session
        - Browse courses and sections
        - Download PDF resources
        - Save skipped files to CSV
        - Close session
        """

        self.start_session()
        if len(self.years) != 0:
            for year in self.years:
                self.look_courses(year)
        else:
            self.look_courses()
        self.no_downloaded.to_csv(os.path.join(self.dest_folder, "no_downloaded.csv"), 
                                  index=False, 
                                  encoding='utf-8')
            
        self.session.close()


# Entrypoint
config = Config()
main = Main(config=config)
main.main()