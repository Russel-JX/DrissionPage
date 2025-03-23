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

# 数据库连接
db = HotelDatabase()
def get_city_list():
    #从数据库读取可用城市列表。默认返回所有城市
    return db.query_data('city')  # 假设 city 表中有城市信息

# 爬取酒店信息的线程函数
def crawl_city_data(city, result_queue):
    """
    爬取指定城市的酒店信息
    :param city: 城市名称
    :param result_queue: 用于存储爬取结果的队列
    """
    try:
        print(f"开始爬取城市：{city['name']}")
        page = ChromiumPage()

        # 获取酒店列表及价格信息
        page.get(f"https://example.com/hotels?city={city['name']}")
        hotels = page.eles('.hotel-card')  # 假设酒店卡片的 CSS 类名为 .hotel-card

        for hotel in hotels:
            hotel_data = {
                'name': hotel.ele('.hotel-name').text,
                'price': hotel.ele('.hotel-price').text,
                'city': city['name']
            }
            # 获取积分信息
            hotel_data['points'] = hotel.ele('.hotel-points').text

            # 保存酒店价格和积分信息到数据库
            db.insert_data('hotelprice', hotel_data)

            # 获取酒店详情页信息
            hotel_detail_url = hotel.ele('.hotel-detail-link').attr('href')
            page.get(hotel_detail_url)
            hotel_details = {
                'address': page.ele('.hotel-address').text,
                'features': page.ele('.hotel-features').text
            }
            hotel_data.update(hotel_details)

            # 保存酒店详情信息到数据库
            db.insert_data('hotel', hotel_data)

        # 将结果存入队列
        result_queue.put(f"城市 {city['name']} 爬取完成")
        print(f"城市 {city['name']} 爬取完成")
        page.quit()

    except Exception as e:
        print(f"爬取城市 {city['name']} 时发生错误：{e}")
        result_queue.put(f"城市 {city['name']} 爬取失败：{e}")

# 主函数
def main():
    # 读取城市列表
    cities = get_city_list()

    # 创建线程队列
    threads = []
    result_queue = Queue()

    # 启动多线程爬取
    for city in cities:
        thread = threading.Thread(target=crawl_city_data, args=(city, result_queue))
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
    db.insert_data('loadboard', {'status': 1, 'updatetime': time.strftime('%Y-%m-%d %H:%M:%S')})

    print("所有城市爬取完成")

# 执行主函数
if __name__ == '__main__':
    main()
