from selenium.webdriver.chrome.options import Options

from selenium import webdriver

options = Options()
options.add_argument("--disable-features=HttpsUpgrades,HttpsFirstModeV2")
options.add_argument("--ignore-certificate-errors")

driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)
driver.get("http://app:8000/usuarios/novo")
print(driver.page_source[:200])
driver.quit()
