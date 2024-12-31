import os
import sys
import time
import csv
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
# 指定ChromeDriver的路径
s = Service(executable_path='/usr/local/bin/chromedriver')
# 如果您使用的是Chrome Beta，还需要指定Chrome Beta的路径
options = webdriver.ChromeOptions()
options.binary_location = '/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
# 使用Service对象创建WebDriver
driver = webdriver.Chrome(service=s, options=options)

def login():
    driver.get('https://www.imdb.com/registration/signin')
    element = driver.find_element(By.ID, 'signin-perks')
    driver.execute_script("arguments[0].setAttribute('style', 'color: red;font-size: larger; font-weight: 700;')", element)
    driver.execute_script("arguments[0].innerText = '请登录自己的IMDB账号, 程序将等待至登录成功。'", element)
    current_url = driver.current_url
    WebDriverWait(driver, 600).until(EC.url_changes(current_url))
    new_url = driver.current_url
    if new_url == 'https://www.imdb.com/?ref_=login':
        print('IMDB登录成功')
    return driver

def mark(is_unmark=False, rating_adjust=-1):
    driver = login()
    success_marked = 0
    success_unmarked = 0
    cannot_found = []
    already_marked = []
    never_marked = []
    file_name = os.path.dirname(os.path.abspath(__file__)) + '/movie.csv'
    temp_file_name = os.path.dirname(os.path.abspath(__file__)) + '/movie_temp.csv'  # 临时文件用于更新

    # 读取上次的进度
    last_marked_line = 0
    if os.path.exists(temp_file_name):
        with open(temp_file_name, 'r', encoding='utf-8') as f:
            last_marked_line = f.readline().strip()
            # 确保 last_marked_line 是数字，如果不是，则设置为 0
            if not last_marked_line.isdigit():
                last_marked_line = 0
            else:
                last_marked_line = int(last_marked_line)

    with open(file_name, 'r', encoding='utf-8') as file, open(temp_file_name, 'w', encoding='utf-8') as temp_file:
        content = csv.reader(file, lineterminator='\n')
        for i, line in enumerate(content):
            if i < last_marked_line:  # 跳过已经处理过的行
                continue

            if not line[1]:
                line[1] = random.choice([3, 3.5, 4])
            movie_name, movie_rate, imdb_id = line
            movie_rate = float(movie_rate) * 2 + rating_adjust + random.choice([-1, 0, 1])
            if not imdb_id or not imdb_id.startswith('tt'):
                cannot_found.append(movie_name)
                print('无法在IMDB上找到：', movie_name)
                temp_file.write(str(i) + '\n')  # 更新进度
                continue

            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'suggestion-search')))
            search_bar = driver.find_element(By.ID, 'suggestion-search')
            search_bar.send_keys(imdb_id)
            search_bar.submit()
            time.sleep(3)
            try:
                if is_unmark:
                    driver.find_element(By.XPATH, '//div[@data-testid="hero-rating-bar__user-rating__score"]')
                else:
                    driver.find_element(By.XPATH, '//div[@data-testid="hero-rating-bar__user-rating"]')
            except NoSuchElementException:
                if is_unmark:
                    never_marked.append(f'{movie_name}({imdb_id})')
                    print(f'并没有在IMDB上打过分：{movie_name}({imdb_id})')
                else:
                    already_marked.append(f'{movie_name}({imdb_id})')
                    print(f'已经在IMDB上打过分：{movie_name}({imdb_id})')
            else:
                try:
                    rate_btn_xpath = '//div[@data-testid="hero-rating-bar__user-rating"]/button'
                    # 点击评分按钮
                    driver.find_element(By.XPATH, rate_btn_xpath).click()

                    if is_unmark:
                        driver.find_element(By.XPATH, "//div[@class='ipc-starbar']/following-sibling::button[2]").click()
                        print(f'电影删除打分成功：{movie_name}({imdb_id})')
                        success_unmarked += 1
                    else:
                        # 新版IMDB页面如果不先将鼠标移动到相应星星处再点击则点击无效
                        star_ele_xpath = f'//button[@aria-label="Rate {movie_rate}"]'
                        WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.XPATH, star_ele_xpath))
                        )
                        star_ele = driver.find_element(By.XPATH, star_ele_xpath)
                        mark_action = ActionChains(driver).move_to_element(star_ele).click()
                        mark_action.perform()
                        confirm_rate_ele_xpath = "//div[@class='ipc-starbar']/following-sibling::button"
                        driver.find_element(By.XPATH, confirm_rate_ele_xpath).click()
                        print(f'电影打分成功：{movie_name}({imdb_id}) → {movie_rate}★')
                        success_marked += 1
                except TimeoutException:
                    print(f"等待评分按钮可见超时：{movie_name}{imdb_id}")
                except NoSuchElementException:
                    print(f"找不到评分按钮：{movie_name}{imdb_id}")
            temp_file.write(str(i) + '\n')  # 更新进度
            time.sleep(1)
    driver.close()

    # 重命名临时文件为原文件，以便下次继续
    os.remove(file_name)
    os.rename(temp_file_name, file_name)

    print('***************************************************************************')
    if is_unmark:
        print(f'成功删除了 {success_unmarked} 部电影的打分')
        print(f'有 {len(cannot_found)} 部电影没能在IMDB上找到：', cannot_found)
        print(f'有 {len(never_marked)} 部电影并没有在IMDB上打过分：', never_marked)
    else:
        print(f'成功标记了 {success_marked} 部电影')
        print(f'有 {len(cannot_found)} 部电影没能在IMDB上找到：', cannot_found)
        print(f'有 {len(already_marked)} 部电影已经在IMDB上打过分：', already_marked)
    print('***************************************************************************')

if __name__ == '__main__':
    if not os.path.exists(os.path.dirname(os.path.abspath(__file__)) + '/movie.csv'):
        print('未能找到CSV文件，请先导出豆瓣评分，请参照：',
              'https://github.com/fisheepx/douban-to-imdb')
        sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'unmark':
        mark(True)
    elif len(sys.argv) > 1:
        if sys.argv[1] not in ['-2', '-1', '0', '1', '2']:
            print('分数调整范围不能超过±2分(默认 -1分)，请参照：',
                  'https://github.com/fisheepx/douban-to-imdb')
            sys.exit()
        else:
            mark(False, int(sys.argv[1]))
    else:
        mark()