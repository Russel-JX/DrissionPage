from threading import Thread, Semaphore, Lock
from queue import Queue
from LoadPriceHIG import LoadPriceHIG
from datetime import datetime, timedelta
from util.StrUtil import StrUtil
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为 DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式（包括时间戳）
    datefmt='%Y-%m-%d %H:%M:%S',  # 设置时间格式
    handlers=[
        logging.FileHandler('DrissionPage/hotel/logs/hotel.log'),  # 将日志输出到 logs/my_log.log 文件
        logging.StreamHandler()  # 同时将日志输出到控制台
    ]
)

#常量定义
MAX_MAIN_THREAD_COUNT = 2 #同时运行的城市（主线程）数
MAX_SUB_THREAD_TAB_COUNT = 4 #同时运行的tab（子线程。1个酒店的一种数据请求）数
MAX_DAYS_COUNT = 2 #请求的总天数
# CITIES = ['北京']  # 城市列表
CITIES = ['北京', '上海', '广州']  # 城市列表

# 限制同时运行的城市数量（4 个城市，即 8 个 tab）
city_semaphore = Semaphore(MAX_MAIN_THREAD_COUNT)
tab_pool = list(range(MAX_SUB_THREAD_TAB_COUNT))  # 4 个 tab 的索引
tab_lock = Lock()  # 用于保护 tab_pool 的线程锁

def process_city(loader, city, result_queue):
    version = datetime.now().strftime('%Y-%m-%d %H:%M')
    """
    处理单个城市的数据（父线程）
    """
    with city_semaphore:  # 限制同时运行的城市数量
        try:
            # 分配两个 tab 索引
            with tab_lock:
                if len(tab_pool) < 2:
                    raise RuntimeError("没有足够的 tab 可用")
                #每次从列表中按顺序移除1个并返回。分别返回:0,1,2,3,4...
                price_tab_index = tab_pool.pop(0)
                points_tab_index = tab_pool.pop(0)

            # logging.info(f"城市 {city} 分配到的 tab 索引：价格 tab={price_tab_index}, 积分 tab={points_tab_index}")

            pricedate = datetime.today()

            days_start_time = time.time()

            for i in range(MAX_DAYS_COUNT):  # 爬取两天的数据
                # 构造 URL
                params = loader.getHIGParams(city, pricedate)
                su = StrUtil()
     
                # 价格信息URL
                priceURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false'
                # 积分信息URL
                pointsURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=POINTS&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=IVANI&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
                priceURL = su.replace_URLParam(priceURL, params)
                pointsURL = su.replace_URLParam(pointsURL, params)
                
                # 创建子线程处理价格和积分数据
                price_result = []
                points_result = []

                def fetch_price():
                    nonlocal price_result
                    start_time = time.time()
                    price_result = loader.loadData(city, pricedate, priceURL, 'price', tab_index=price_tab_index)
                    save(loader, version, pricedate, price_result)
                    end_time =  time.time()
                    logging.info(f"***price 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的1天数据量：{len(price_result)}，耗时：{end_time - start_time:.2f} 秒)")

                def fetch_points():
                    nonlocal points_result
                    start_time = time.time()
                    points_result = loader.loadData(city, pricedate, pointsURL, 'points', tab_index=points_tab_index)
                    # logging.info(f"points 城市 {city} 日期 {pricedate} 的1天数据：{points_result}")
                    save(loader, version, pricedate, points_result)
                    end_time =  time.time()
                    logging.info(f"***points 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的1天数据量：{len(points_result)}，耗时：{end_time - start_time:.2f} 秒)")

                # 启动子线程
                price_thread = Thread(target=fetch_price)
                points_thread = Thread(target=fetch_points)
                price_thread.start()
                points_thread.start()

                # 等待子线程完成
                price_thread.join()
                points_thread.join()

                # 更新日期
                pricedate += timedelta(days=1)
            days_end_time = time.time()
            logging.info(f"==={city} {MAX_DAYS_COUNT} 天 总耗时：{days_end_time - days_start_time:.2f} 秒)")
            result_queue.put(f"城市 {city} {MAX_DAYS_COUNT} 天数据爬取完成")
        except Exception as e:
            result_queue.put(f"城市 {city} 数据爬取失败：{e}")

        finally:
            # 释放 tab 索引
            with tab_lock:
                tab_pool.append(price_tab_index)
                tab_pool.append(points_tab_index)
            logging.info(f"城市 {city} 释放了 tab 索引：价格 tab={price_tab_index}, 积分 tab={points_tab_index}")

    #保存1个城市的1个酒店的1天价格信息，到DB
def save(loader, version, pricedate, hotel_list):
    #转一下

    # 保存到数据库
    for hotel in hotel_list:
        hotel['version'] = version
        hotel['pricedate'] = pricedate
        loader.db.insert_data('hotelprice', hotel)

def main():
    cities = CITIES

    result_queue = Queue()
    loader = LoadPriceHIG()

    try:
        """"
        默认的page会打开一个tab，加上这里指定打开的固定tab数。总tab数比定义的多1个。
        操作定义的tab时，还是从0开始（0不会操作到page默认tab）
        处理一个单个数据时，耗时平均：15秒
        03.26
        3cityx2dayx2type    154s    平均12s/city*day*type
        """
        # 打开 8 个 tab 页面（4 个城市，每个城市 2 个 tab）
        loader.open_tabs(MAX_SUB_THREAD_TAB_COUNT)

        cities_start_time = time.time()

        # 多线程处理每个城市的数据
        threads = []
        for city in cities:
            thread = Thread(target=process_city, args=(loader, city, result_queue))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        cities_end_time = time.time()
        logging.info(f"###{len(cities)} 个城市， {MAX_DAYS_COUNT} 天 总耗时：{cities_end_time - cities_start_time:.2f} 秒)")

        # 打印结果
        while not result_queue.empty():
            logging.info(result_queue.get())

    finally:
        # 关闭浏览器
        loader.close_browser()


if __name__ == '__main__':
    main()