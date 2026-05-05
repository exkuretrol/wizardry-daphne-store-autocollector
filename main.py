import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def main():
    if len(sys.argv) <= 1:
        print("USER_ID needed. Usage: python main.py [USER_ID]")
        sys.exit()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options)
    #does not appear that the code needs to emulate geolcation data to force the EN store
    #(which is necessary for the user_id_field variable)
    actions = ActionChains(driver)
    wait = WebDriverWait(driver, 10)

    driver.get('https://store.wizardry.info/')

    # Dismiss GDPR consent overlay before it intercepts login button click
    gdpr_button = wait.until(EC.element_to_be_clickable((By.ID, "reject-button")))
    gdpr_button.click()

    user_id_field = wait.until(EC.element_to_be_clickable((By.XPATH, "(//input[@placeholder='Enter your user ID'])")))
    login_button = driver.find_element(By.XPATH, "(//button[@data-testid='fast-login-button-authorization-user-id'])")

    actions.move_to_element(login_button).perform()
    user_id_field.send_keys(sys.argv[1])
    login_button.click()
    time.sleep(2.5)

    free_gems_button = driver.find_element(By.XPATH, "(//button[@data-sku='jp.co.drecom.wizardry.daphne.X_gem900010'])")
    if(not free_gems_button.is_enabled()):
        print("Free gems button is not enabled; likely already clicked. Exiting.")
        driver.quit()
        sys.exit()
    actions.move_to_element(free_gems_button).perform()
    free_gems_button.click()
    time.sleep(2.5)

    driver.quit()


if __name__ == '__main__':
    main()