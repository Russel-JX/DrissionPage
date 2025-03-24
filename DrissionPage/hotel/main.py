#爬虫主入口。启动多线程，爬取酒店信息
# 1. 读取可用酒店的城市列表(city表)
# 2. 启动多线程，爬取酒店信息
    #2.1 每个城市一个线程。一个线程中：
        # 发起请求，获取酒店列表及价格信息；
        # 发起请求，获取酒店列表及积分信息
        # 对具体相同酒店，DB记录价格和积分信息
    #2.2 对具体相同酒店，DB记录酒店详情页信息
# 3. 保存酒店信息
# 4. 保存爬取日志
# 5. 保存爬取状态
# 6. 保存爬取结果
# 7. 保存爬取错误
# 8. 保存爬取统计
# 9. 保存爬取配置
# 10. 保存爬取参数
# 11. 保存爬取数据  

import threading
import time
from queue import Queue
from DrissionPage import ChromiumPage
from util.HotelDatabase import HotelDatabase
from LoadPriceHIG import LoadPriceHIG


# 数据库连接
db = HotelDatabase()
# 爬取酒店信息的函数
loader = LoadPriceHIG()
def get_city_list():
    #从数据库读取可用城市列表。默认返回所有城市
    return db.query_data('city')  # 假设 city 表中有城市信息

# 主函数
def main():
    # 读取城市列表
    # cities = get_city_list()
    # cities = [{'name':'上海'}] 
    cities = [{'name':'北京'},
              {'name':'上海'}] 

    # 创建线程队列
    threads = []
    #队列收集多个线程的执行情况。（哪些运行成功，哪些失败）
    result_queue = Queue()

    # 启动多线程爬取
    for city in cities:
        print(f'====线程开始！====')
        #汉字城市转码
        # encoded_city = urllib.parse.quote(city.get('name'))  不用编码，因为url替换式工具类中已经编码了
        # today = datetime.today().strftime('%Y-%m-%d') # 今天日期2025-03-23
        # version = datetime.now().strftime('%Y-%m-%d %H') # 当前日期时间2025-03-23 15

        thread = threading.Thread(target=loader.getHotelInfo, args=(city.get('name'), result_queue))

        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 保存爬取日志
    while not result_queue.empty():
        result = result_queue.get()
        print(result)  # 打印日志，实际可保存到数据库或文件

    # 保存爬取状态
    db.insert_data('loadboard', {'city':city, 'status': 1, 'updatetime': time.strftime('%Y-%m-%d %H:%M:%S')})

    print("所有城市爬取完成")

# 执行主函数
if __name__ == '__main__':
    main()
