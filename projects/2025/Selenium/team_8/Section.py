from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time

class Section:
    """
    Represents a single section within a Moodle course.

    This class handles interactions with a course section, including
    opening the section, retrieving its resources, and filtering
    them by type (PDF or other).

    Attributes
    ----------
    session : MoodleSession
        Active Moodle session used to interact with the page.
    section_element : WebElement
        Selenium WebElement representing the section tile.
    driver : selenium.webdriver.Chrome
        The WebDriver instance from the session.
    wait : WebDriverWait
        Explicit wait handler from the session.
    id : str
        Unique identifier of the section.
    name : str
        Name/title of the section.
    resources : list[WebElement]
        List of resource elements found within the section.
    """

    def __init__(self, session, section_element):
        """
        Initialize a Section object.

        Parameters
        ----------
        session : MoodleSession
            The active Moodle session.
        section_element : WebElement
            Selenium WebElement representing the section tile.
        """

        self.session = session
        self.section_element = section_element
        self.driver = self.session.driver
        self.wait = self.session.wait
        self.id = self.section_element.get_attribute("data-section")
        self.name = self.section_element.find_element(
            By.XPATH, f"//*[@id='tileTextin-{self.id}']/h3"
            ).text.strip()
       
    def open(self):
        """
        Open the section by clicking its tile.

        Waits briefly to ensure the section content is loaded.
        """

        self.section_element.click()
        print(f'Section: {self.name}')
        time.sleep(2) # Wait for the section to load

    def get_resources_container(self):
        """
        Retrieve the container element holding all resources in the section.

        Returns
        -------
        WebElement
            The container element for section resources.
        """

        resourcer_container = self.wait.until(EC.presence_of_element_located((By.ID, f"section-{self.id}")))
        return resourcer_container
    
    def get_resources(self):
        """
        Retrieve all resources in the section, separating PDFs and others.

        Returns
        -------
        tuple[list[tuple[str, str]], list[tuple[str, str]]]
            - First list: PDFs as tuples (name, URL)
            - Second list: other resources as tuples (name, URL)
        """

        resources_container = self.get_resources_container()
        self.resources = resources_container.find_elements(By.CSS_SELECTOR, "li.modtype_resource")
        pdf_resources = self.filter_pdf_resources()
        other_resources = self.filter_others_resources()
        return pdf_resources, other_resources

    def filter_pdf_resources(self):
        """
        Filter resources to only include PDF files.

        Returns
        -------
        list[tuple[str, str]]
            List of PDF resources as tuples (name, URL).
        """

        resources = [(res.get_attribute("data-title"), res.get_attribute("data-url"))
                      for res in self.resources if res.get_attribute("data-modtype") == "resource_pdf"]

        return resources
    
    def filter_others_resources(self):
        """
        Filter resources to include non-PDF types (standard resources and URLs).

        Returns
        -------
        list[tuple[str, str]]
            List of other resources as tuples (name, URL).
        """
        
        resources = [(res.get_attribute("data-title"), res.get_attribute("data-url"))
                      for res in self.resources if res.get_attribute("data-modtype") in ['resource', 'url']]

        return resources
