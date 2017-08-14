# -*- coding: utf-8 -*-
import urllib.request
import urllib.error
import os
import logging
import re
import queue
import threading
import time
import random

logging.basicConfig(filename='log.log',
                    format='%(asctime)s %(threadName)s %(levelname)s %(module)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S %p',
                    level=logging.INFO)
# 定义一个Handler打印INFO及以上级别的日志到sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# 设置日志打印格式
formatter = logging.Formatter('%(asctime)s %(threadName)s %(levelname)s %(module)s:%(message)s')
console.setFormatter(formatter)
# 将定义好的console日志handler添加到root logger
logging.getLogger('').addHandler(console)

# 电影url正则匹配
reg_str = r"https://v\d.wuso.tv/wp-content/uploads/[0-9]{4}/[0-9]{2}/[a-zA-Z0-9]+.mp4"
pattern = re.compile(reg_str)
movie_url_queue = queue.Queue()
forum_url = "https://wuso.me/thread-"
global start_idx, end_idx, flag, exit_thread_count
flag = True
exit_thread_count = 0
# 电影大小（M），超过放弃下载
max_movie_size = 80
# 下载线程数
consume_url_thread_num = 3
# url爬取线程数
produce_url_thread_num = 8
# 下载保存路径
path = "E:/movie"
# 轮训论坛帖子起始index,可自己查看网站后调整
start_idx = 110000
end_idx = 120000
user_agents = ["Mozilla/5.0(Macintosh;U;IntelMacOSX10_6_8;en-us)AppleWebKit/534.50(KHTML,likeGecko)"
               "Version/5.1Safari/534.50",
               "User-Agent:Mozilla/5.0(compatible;MSIE9.0;WindowsNT6.1;Trident/5.0",
               "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/59.0.3071.115 Safari/537.36",
               "User-Agent:Mozilla/5.0(Macintosh;IntelMacOSX10.6;rv:2.0.1)Gecko/20100101Firefox/4.0.1"]


def download_movie(referer_url, movie_url, local_path):
    logging.info("try download movie:" + movie_url)
    try:
        req = urllib.request.Request(movie_url)
        req.add_header("user-agent", user_agents[random.randint(0, 3)])
        req.add_header("Accept-Encoding", "identity;q=1, *;q=0")
        req.add_header("Referer", referer_url)
        req.add_header("keep-live", "false")
        with urllib.request.urlopen(req) as response:
            mime_info = response.info()
            if mime_info.get("Content-type") == "video/mp4":
                file_name = movie_url.split("/")[-1]
                if int(mime_info.get("content-length")) > max_movie_size * 1024 * 1024:
                    logging.info("{0} size is {1}, give up it".format(file_name, mime_info.get("content-length")))
                    return
                logging.info("downloading movie {}".format(file_name))
                with open("{0}/{1}".format(local_path, file_name), "wb") as code:
                    code.write(response.read())
                logging.info("download movie over {}".format(file_name))
                response.close()
            else:
                logging.info("[{0}] is not a movie's url".format(movie_url))
                return
    except urllib.error.HTTPError as e:
        logging.error("download file fail[{0}] ->{1}:{2}".format(movie_url, e.code, e.reason))
    except Exception as e:
        logging.error(e.reason)


def parse_movie_url(html_url):
    logging.info("parsing url[{0}]".format(html_url))
    try:
        req = urllib.request.Request(html_url)
        req.add_header("user-agent", user_agents[0])
        response = urllib.request.urlopen(req, timeout=20)
        html_text = response.read().decode('utf-8', 'ignore')
        response.close()
        urls = re.findall(pattern, html_text)
        key_urls = {html_url: urls}
        return key_urls
    except Exception as e:
        logging.error(e)
    return None


def produce_url():
    global start_idx, end_idx, flag, exit_thread_count
    while flag:
        if start_idx <= end_idx:
            html_url = forum_url + str(start_idx) + "-1-1.html"
            start_idx += 1
            key_urls = parse_movie_url(html_url)
            if key_urls is not None:
                for key in key_urls.keys():
                    for url in key_urls.get(key):
                        movie_url_queue.put("{0} {1}".format(key, url))
        else:
            flag = False
    exit_thread_count += 1
    logging.info("{0} exit".format(threading.current_thread().getName()))


def consume_url():
    while not  exit_thread_count == produce_url_thread_num or not movie_url_queue.empty():
        try:
            key_url = movie_url_queue.get(timeout=1)
            logging.info("queue size {0}".format(movie_url_queue.qsize()))
            str_ary = key_url.split(" ")
            # time.sleep(2)  # 这里时间自己设定
            download_movie(str_ary[0], str_ary[1], path)
        except queue.Empty as e:
            pass
    logging.info("{0} exit".format(threading.current_thread().getName()))


def produce_url_thread():
    i = 0
    while i < produce_url_thread_num:
        threading.Thread(target=produce_url, args=()).start()
        i += 1


def consume_url_thread():
    i = 0
    while i < consume_url_thread_num:
        threading.Thread(target=consume_url, args=()).start()
        i += 1


if __name__ == "__main__":
    if not os.path.exists(path):
        os.mkdir(path)
    produce_url_thread()
    consume_url_thread()
