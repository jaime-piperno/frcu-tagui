from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time
from Course import Course


class MoodleSession:
    """
    Represents a session with the Moodle virtual campus.

    This class handles browser initialization, login, course filtering,
    course search, and retrieval of course cards using Selenium.

    Attributes
    ----------
    user : str
        Username for Moodle login.
    password : str
        Password for Moodle login.
    driver : selenium.webdriver.Chrome
        Chrome WebDriver instance used to automate browser actions.
    wait : WebDriverWait
        Explicit wait handler for synchronizing with dynamic content.
    """

    def __init__(self, user: str, password: str, headless: bool = True, max_wait: int = 10):
        """
        Initialize a Moodle session.

        Parameters
        ----------
        user : str
            Moodle username.
        password : str
            Moodle password.
        headless : bool, optional
            Whether the browser runs in headless mode (default: True).
        max_wait : int, optional
            Maximum time (in seconds) to wait for elements (default: 10).
        """

        self.user = user
        self.password = password

        self.driver = self.start_driver(headless=headless)

        self.wait = WebDriverWait(self.driver, max_wait)

    def start_driver(self, headless: bool = True):
        """
        Configure and start the Chrome WebDriver.

        Parameters
        ----------
        headless : bool, optional
            Whether to start the browser in headless mode (default: True).

        Returns
        -------
        webdriver.Chrome
            A configured Chrome WebDriver instance.
        """

        options = webdriver.ChromeOptions()
        options.add_argument('--disable-notifications')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_argument('--log-level=3')
        if headless:
            options.add_argument('--headless')

        service = Service(log_output='NUL')

        driver = webdriver.Chrome(service=service, options=options)

        return driver
    
    def login(self, url: str):
        """
        Perform login to Moodle with provided credentials.

        Parameters
        ----------
        url : str
            Login page URL of the Moodle virtual campus.
        """
                
        self.driver.get(url)

        # Locate login elements
        username_input = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="username"]')))
        password_input = self.driver.find_element(By.XPATH, '//*[@id="password"]')
        login_button = self.driver.find_element(By.XPATH, '//*[@id="loginbtn"]')

        # Enter credentials and submit form
        username_input.send_keys(self.user)
        password_input.send_keys(self.password)
        login_button.click()

        print("Login completed")

        # Wait for login to complete
        time.sleep(5)

    def change_num_courses_shown(self):
        """
        Change the dashboard setting to display all courses.
        """
        
        num_courses_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[4]/div/div[2]/div/section/div/aside/section/div/div/div[1]/div[2]/div/div/div[2]/div/div/div/button')))
        num_courses_btn.click()
        time.sleep(1)

        all_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[4]/div/div[2]/div/section/div/aside/section/div/div/div[1]/div[2]/div/div/div[2]/div/div/div/div/a[2]')))
        all_btn.click()
        time.sleep(3)

    def change_type_courses_shown(self):
        """
        Change the dashboard filter to show all types of courses.
        """

        type_courses_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="groupingdropdown"]')))
        type_courses_btn.click()
        time.sleep(1)

        all_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[4]/div/div[2]/div/section/div/aside/section/div/div/div[1]/div[1]/div/div[1]/ul/li[2]/a')))
        all_btn.click()
        time.sleep(3)

    def change_view_courses_shown(self):
        """
        Change the course display style to 'Tarjeta'.
        """

        view_courses_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="displaydropdown"]')))
        view_courses_btn.click()
        time.sleep(1)

        card_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[4]/div/div[2]/div/section/div/aside/section/div/div/div[1]/div[1]/div/div[4]/ul/li[1]/a')))
        card_btn.click()
        time.sleep(3)

    def get_course_cards(self, year=None):
        """
        Retrieve all visible course cards, optionally filtering by year.

        Parameters
        ----------
        year : int, optional
            Academic year used as a filter for searching courses.

        Returns
        -------
        list[Course]
            A list of `Course` objects representing the available courses.
        """

        if year:
            print(f'YEAR: {year}')
            self.search_courses(year)
            
        course_cards = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card.dashboard-card")))
        time.sleep(3)

        return [Course(session=self,
                       card_element=card) for card in course_cards]
    
    def search_courses(self, year):
        """
        Search courses by entering the academic year in the search bar.

        Parameters
        ----------
        year : int
            Academic year to search for.
        """

        search_input = self.wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div[4]/div/div[2]/div/section/div/aside/section/div/div/div[1]/div[1]/div/div[2]/div/div/input')))
        search_input.send_keys(year)
        time.sleep(2)

    def clear_search_courses(self):
        """
        Clear the course search filter.
        """

        clear_search_btn = self.wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div[4]/div/div[2]/div/section/div/aside/section/div/div/div[1]/div[1]/div/div[2]/div/div/button')))
        clear_search_btn.click()
        time.sleep(2)

    def get_cookies(self):
        """
        Get all cookies from the current browser session.

        Returns
        -------
        list[dict]
            A list of cookies in dictionary format.
        """

        cookies = self.driver.get_cookies()
        return cookies
    
    def close(self):
        """
        Close the browser and terminate the session.
        """
        
        self.driver.quit()
