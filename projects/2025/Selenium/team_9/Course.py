from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from Section import Section
import time

class Course:
    """
    Represents a single course in Moodle.

    This class handles interactions with a course card, including opening
    the course page, retrieving the course name, and obtaining its sections.

    Attributes
    ----------
    session : MoodleSession
        Active Moodle session used to interact with the page.
    wait : WebDriverWait
        Explicit wait handler inherited from the session.
    card_element : WebElement
        Selenium WebElement representing the course card in the dashboard.
    id : str
        Unique identifier for the course.
    subject_card : WebElement
        The full course card element located in the DOM.
    name : str
        Name of the course (retrieved after calling `get_name()`).
    """

    def __init__(self, session, card_element):
        """
        Initialize a Course object.

        Parameters
        ----------
        session : MoodleSession
            The active Moodle session.
        card_element : WebElement
            Selenium WebElement representing the course card.
        """

        self.session = session
        self.wait = self.session.wait
        self.card_element = card_element
        self.id = self.card_element.get_attribute("data-course-id")
        self.subject_card = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'div.card[data-course-id="{self.id}"]')))

    def open(self):
        """
        Open the course page by clicking the course card link.

        Waits briefly to ensure the course page loads.
        """

        self.subject_card.find_element(By.CSS_SELECTOR, "a").click()
        
        time.sleep(3) # Wait for the course page to load

    def get_name(self):
        """
        Retrieve and store the course name from the course page header.
        """

        self.name = self.wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="page-header"]/div/div[2]/div[1]/div/div/h1'))
            ).text.strip()
    
    def get_sections(self):
        """
        Retrieve all sections available in the course.

        Returns
        -------
        list[Section]
            A list of Section objects representing the course sections.
        """
        
        sections = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.tile.tile-clickable"))) 

        return [Section(session=self.session,
                        section_element=el) for el in sections]