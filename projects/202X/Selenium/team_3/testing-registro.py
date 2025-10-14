from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import random
import string
import re
import time

brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"





class RegisterBraveTest:
    def __init__(self, url, headless=False, brave_path=None):
        self.url = url
        self.headless = headless
        self.brave_path = brave_path
        self.driver = None

    def setup_driver(self):
        """Configura el driver de Chrome"""
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        # options.add_argument('--headless')  # Descomentar para modo sin interfaz
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def generate_password(self, length=10, specials=True):
        chars = string.ascii_letters + string.digits
        if specials:
            chars += "!@#$%&*?"
        return "".join(random.choice(chars) for _ in range(length))

    def generate_emails(self, base="correos"):
        domains = ["EMAIL.COM","EMAIL"]
        emails = []
        for d in domains:
            emails.append(f"{base}{d}")
            emails.append(f"{base.capitalize()}@{d.lower()}")
        return emails

    def is_email_valid(self, email):
        regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return re.match(regex, email) is not None

    def run_test(self, username, email, password):
        result = {"user":username, "email": email, "password": password, "ok": False, "msg": ""}
        try:
            self.driver.get(self.url)
            time.sleep(1)

            # Campos (ajusta si tus inputs tienen otro atributo)
            user_input = self.driver.find_element(By.CSS_SELECTOR, '#Input_UserName')
            email_input = self.driver.find_element(By.CSS_SELECTOR, '#Input_EmailAddress')
            pwd_input = self.driver.find_element(By.CSS_SELECTOR, '#Input_Password')
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')

            # Llenar formulario
            user_input.clear()
            email_input.clear()
            pwd_input.clear()
            user_input.send_keys(username)
            email_input.send_keys(email)
            pwd_input.send_keys(password)

            # Click en registrarse
            submit_btn.click()
            time.sleep(2)

            # Heurística: si la URL cambia => éxito
            if "register" not in self.driver.current_url.lower():
                result["ok"] = True
                result["msg"] = "Registro exitoso"
            else:
                result["msg"] = "Registro rechazado"
        except Exception as e:
            result["msg"] = f"Error: {str(e)}"
        return result

    def run_batch(self, n_passwords=3):
        self.setup_driver()
        results = []
        try:
            emails = self.generate_emails()
            for indice, email in enumerate(emails):
                indice+=100
                print(f"El email '{email}' está en el índice {indice}.")
                # Contraseña válida fija
                res = self.run_test(f"testuser{indice}", email, "User100@")
                results.append(res)

                # Contraseñas aleatorias
                for _ in range(n_passwords):
                    pwd = self.generate_password()
                    res = self.run_test(f"testuser{indice}", email, pwd)
                    results.append(res)
        finally:
            self.driver.quit()
        return results


if __name__ == "__main__":
    tester = RegisterBraveTest(
        url="https://localhost:44332/Account/Register?returnUrl=%2Fconnect%2Fauthorize%3Fresponse_type%3Dcode%26client_id%3DJempaTV_App%26state%3DeUxXNjlnbnJGSWIxczA5UU5sd2RHaFBBSnJ6WE9DfkhDZDliajhmRnktZWkw%26redirect_uri%3Dhttp%253A%252F%252Flocalhost%253A4200%26scope%3Dopenid%2520JempaTV%26code_challenge%3DcNYFsGsATcZv7p6GFD8crn717AhCL6ITXroPlBRrIao%26code_challenge_method%3DS256%26nonce%3DeUxXNjlnbnJGSWIxczA5UU5sd2RHaFBBSnJ6WE9DfkhDZDliajhmRnktZWkw%26culture%3Des%26ui-culture%3Des",  # ⚠️ Cambia a tu URL real
        headless=False,
        brave_path="C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"  # ruta en Windows
    )

    results = tester.run_batch(n_passwords=2)

    for r in results:
        print(r)
