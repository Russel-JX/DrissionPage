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
MAX_MAIN_THREAD_COUNT = 1 #同时运行的城市（主线程）数
MAX_SUB_THREAD_TAB_COUNT = 2 #同时运行的tab（子线程。1个酒店的一种数据请求）数
MAX_DAYS_COUNT = 2 #请求的总天数
CITIES = ['北京']  # 城市列表
# CITIES = ['上海'] 
# CITIES = ['北京', '上海', '广州'] 
# CITIES = ['北京', '上海', '广州', '深圳', '南京', '武汉', '成都', '杭州'] 


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
                    #每个线程，单独loader单独DB，防止数据库连接中断.loader4Load独立，只负责DB插入。
                    loader4Load = LoadPriceHIG()
                    nonlocal price_result
                    start_time = time.time()
                    price_result = loader.loadData(city, pricedate, priceURL, 'price', tab_index=price_tab_index)
                    save(loader4Load, version, pricedate, price_result)
                    end_time =  time.time()
                    logging.info(f"***price 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的记录数：{len(price_result)}，耗时：{end_time - start_time:.2f} 秒)")

                def fetch_points():
                     #每个线程，单独loader单独DB，防止数据库连接中断
                    loader4Load = LoadPriceHIG()
                    nonlocal points_result
                    start_time = time.time()
                    points_result = loader.loadData(city, pricedate, pointsURL, 'points', tab_index=points_tab_index)
                    # logging.info(f"points 城市 {city} 日期 {pricedate} 的1天数据：{points_result}")
                    save(loader4Load, version, pricedate, points_result)
                    end_time =  time.time()
                    logging.info(f"***points 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的记录数：{len(points_result)}，耗时：{end_time - start_time:.2f} 秒)")

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
    result_queue = Queue()
    loader = LoadPriceHIG()
    
    # # 从 city 表中查询所有城市名称
    query_result = loader.db.query_data(
        'city', 
       conditions="hotelavailable != 0 AND level IN (0, 1) ORDER BY level ASC")
    cities = [row['name'] for row in query_result]  # 提取 name 列的值
    logging.info(f"从DB得到城市列表：{cities}")

    #测试用城市列表
    cities = CITIES

    try:
        """"
        频率：至少1-5h跑一遍
        默认的page会打开一个tab，加上这里指定打开的固定tab数。总tab数比定义的多1个。
        操作定义的tab时，还是从0开始（0不会操作到page默认tab）
        处理一个单个数据时，耗时平均：15秒。
        处理一个城市下所有酒店的1天数据（同事包括积分和价格），耗时平均：30秒。
        03.26
        city day type totaltime(s) average  总记录 条数据/分钟
        3 2 2 154 12    5
        8 2 2 347 10.8  6
        1 3 2 48  x     251    313    365天，1城，预计1.6小时。
        1 120 2 1393  x     9268    400    4个月数据，23分钟。365天，1城，预计70分钟。
        1 365 2 59分钟  x     4685    79    12个月数据，59分钟。数据明显少了，一天才12条。
        11 30 2 20分钟 xx  349 17    17:52执行到18:12共20分钟（一分钟17条数据，速度还可以），后来一直到17:00都在报错，且无数据产生
        """
        """
        洲际有的城市，因为没有酒店或本市洲际很少，页面展示包含了周边城市的洲际酒店。要排除这种，来避免重复数据。
        对meta数据收集，可以存页面返回的周边城市酒店，但用额外字段local表示(1：本市，0：周边)：
            1.只收集市级酒店(因为市级酒店包括了县级市酒店，县级市不再次收集)
	        2.对市级没有酒店或因为本市很少返回了部分周边酒店的判断：当页面返回的酒店数量<10时，都存入DB，用local字段区分。否则只存入本市的酒店。
            以后在UI可以区分显示。如镇江有1,2,3家洲际酒店，横线下方再展示事先存DB的南京、扬州等地的酒店。
            目的是为了用户可以扩大选择。
        对酒店价格的收集：事先在meta表查询，没有酒店的城市（local=0），直接并不进行收集
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