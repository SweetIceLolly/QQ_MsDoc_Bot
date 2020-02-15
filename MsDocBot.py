# For browser manipulations
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# For CoolQ communication
import asyncio
from cqhttp import CQHttp
import websockets

# For CoolQ data parsing
import json

# For chinese character detection
import re

# For translation
from YoudaoTranslateApi import youdao_translate


MAX_QQMSG_LEN = 417     # A QQ message cannot be sent if it is too long


# Description:  Search MSDN for information of the question
# Args:         question: The question to look up
#               translate_to_chinese: If the result need to be translated to chinese
#               available_len: The maximum length of response text
# Return:       A brief information of the question
def msdn_search(question, need_translation, available_len):
    global driver

    rtnString = ''
    try:
        # Search
        print("Searching for: " + question)
        driver.get('https://docs.microsoft.com/en-us/search/?search=' + question + '&category=Documentation&skip=0')
        WebDriverWait(driver, 5).until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="resultCount-header"]/div[1]/h1')
            ))

        # Click the first link
        element = driver.find_element_by_xpath('//*[@id="main"]/div[2]/ol/li[1]/h2/a')
        print("Link found. Requesting contents...")
        element.click()
        WebDriverWait(driver, 5).until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="main"]')
            ))

        # Parse the information
        try:                                            # Try to get article title
            content_title = driver.find_element_by_tag_name('h1').text
        except:
            content_title = ""
        try:                                            # Try to get a general description
            content_description = driver.find_element_by_xpath('//*[@id="main"]/p[1]').text
        except:
            content_description = ""
        try:                                            # Try to get function parameters
            function_syntax = driver.find_element_by_xpath('//*[@id="main"]/pre[1]/code').text
        except:
            function_syntax = ""

        available_len -= len(driver.current_url) + 10
        if content_title != '':
            if need_translation:
                content_title = youdao_translate(content_title, False)
            rtnString += "文档: " + content_title + "\n"
            available_len -= len(content_title) + 5
        if content_description != '':
            if need_translation:
                content_description = youdao_translate(content_description, False)
            if len(content_description) > available_len:
                content_description = content_description[0:available_len - 8] + "...(省略)"
            rtnString += "描述: " + content_description + "\n"
            available_len -= len(content_description) + 5
        if function_syntax != '':
            if available_len > 13:
                if len(function_syntax) > available_len:
                    function_syntax = function_syntax[0:available_len - 13] + "...(省略)"
                rtnString += "代码:\n" + function_syntax + "\n"
        rtnString += "链接: " + driver.current_url
        print("Contents returned!")
        return rtnString
    except NoSuchElementException:
        print("Link not found!")
        rtnString = "没有找到相关的信息哦！你搜这么骚的东西干嘛？"
    except TimeoutException:
        print("Request timed out!")
        rtnString = "请求超时！大概是因为小水管堵住了吧。"
    except:
        print("Failed to load webpage!")
        rtnString = "加载网页失败！大概冰棍断网了？（那你QQ怎么在线的）"
    return rtnString


# Description:  Handle messages received from QQ
async def qq_msg_handler():
    global bot

    websocket_uri = 'ws://localhost:6700'
    async with websockets.connect(websocket_uri) as websocket:
        data = await websocket.recv()
        data = json.loads(data)
        # Handle group message only
        if data['message_type'] == 'group':
            received_msg = data['message']

            # Respond to the message when the person @me only
            if received_msg[0:22] == '[CQ:at,qq=2315335010] ':
                sender_id = data['sender']['user_id']
                from_group_id = data['group_id']
                received_msg = received_msg.replace('[CQ:at,qq=2315335010] ', '').strip()
                print(str(from_group_id) + ' - ' + str(sender_id) + ': ' + received_msg)
                
                # Check if translation is requested
                need_translation = False
                if received_msg[0:3] == '中文 ':
                    print("Translation requested.")
                    received_msg = received_msg[3:]
                    need_translation = True

                # Translate if there are chinese characters
                chinese_char_detected = False
                if re.search(u'[\u4e00-\u9fff]', received_msg):
                    print('Chinese characters detected.')
                    chinese_char_detected = True
                    received_msg = youdao_translate(received_msg, True)

                if chinese_char_detected:
                    response = '[CQ:at,qq=' + str(sender_id) + ']' + ' '
                    response += "把您的输入翻译成了: " + received_msg + "\n"
                else:
                    response = '[CQ:at,qq=' + str(sender_id) + ']' + "\n"
                available_len = MAX_QQMSG_LEN - len(response)
                response += msdn_search(received_msg, need_translation, available_len)
                print("Responding...")
                print("Message len = " + str(len(response)))
                bot.send_group_msg(group_id=from_group_id, message=response)
                print("Responded!")
                print("")


# Description:  Program entry point
if __name__ == '__main__':
    print("Initalizing chrome...\n")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--log-level=3')
    driver = webdriver.Chrome(options=chrome_options)
    print("Chrome initialized.\n")

    print("Initializing CoolQ...")
    bot = CQHttp(api_root='http://127.0.0.1:5700')
    print("Ready! Waiting for messages...")

    while True:
        try:
            asyncio.get_event_loop().run_until_complete(qq_msg_handler())
        except:
            pass

    driver.quit()