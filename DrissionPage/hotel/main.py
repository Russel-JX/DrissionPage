from threading import Thread, Semaphore, Lock
from queue import Queue
from LoadPriceHIG import LoadPriceHIG
from datetime import datetime, timedelta
from util.StrUtil import StrUtil

# 限制同时运行的城市数量（4 个城市，即 8 个 tab）
# city_semaphore = Semaphore(4)
city_semaphore = Semaphore(2)
# tab_pool = list(range(8))  # 8 个 tab 的索引
tab_pool = list(range(4))  # 4 个 tab 的索引

tab_lock = Lock()  # 用于保护 tab_pool 的线程锁


def process_city(loader, city, result_queue):
    version = datetime.now().strftime('%Y-%m-%d %H')
    """
    处理单个城市的数据（父线程）
    """
    with city_semaphore:  # 限制同时运行的城市数量
        try:
            # 分配两个 tab 索引
            with tab_lock:
                if len(tab_pool) < 2:
                    raise RuntimeError("没有足够的 tab 可用")
                price_tab_index = tab_pool.pop(0)
                points_tab_index = tab_pool.pop(0)

            print(f"城市 {city} 分配到的 tab 索引：价格 tab={price_tab_index}, 积分 tab={points_tab_index}")

            pricedate = datetime.today()
            for i in range(2):  # 爬取两天的数据
                # 构造 URL
                params = loader.getHIGParams(city, pricedate)
                su = StrUtil()
                # priceURL = su.replace_URLParam('https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qPt=CASH', params)
                # pointsURL = su.replace_URLParam('https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qPt=POINTS', params)
                
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
                    price_result = loader.loadData(priceURL, 'price', tab_index=price_tab_index)

                def fetch_points():
                    nonlocal points_result
                    points_result = loader.loadData(pointsURL, 'points', tab_index=points_tab_index)

                # 启动子线程
                price_thread = Thread(target=fetch_price)
                points_thread = Thread(target=fetch_points)
                price_thread.start()
                points_thread.start()

                # 等待子线程完成
                price_thread.join()
                points_thread.join()

                # 合并数据
                # merged_data = loader.merge_hotel_data(price_result, points_result)
                # print(f"城市 {city} 日期 {pricedate} 的合并数据：{merged_data}")

                # 合并数据
                hotel_list = loader.merge_hotel_data(price_result, points_result)
                print(f"城市 {city} 日期 {pricedate} 的合并数据：{hotel_list}")

                # 保存到数据库
                for hotel in hotel_list:
                    hotel['version'] = version
                    hotel['pricedate'] = pricedate
                    loader.db.insert_data('hotelprice', hotel)

                # 更新日期
                pricedate += timedelta(days=1)

            result_queue.put(f"城市 {city} 数据爬取完成")

        except Exception as e:
            result_queue.put(f"城市 {city} 数据爬取失败：{e}")

        finally:
            # 释放 tab 索引
            with tab_lock:
                tab_pool.append(price_tab_index)
                tab_pool.append(points_tab_index)
            print(f"城市 {city} 释放了 tab 索引：价格 tab={price_tab_index}, 积分 tab={points_tab_index}")


def main():
    # cities = ['北京', '上海', '广州', '深圳', '杭州', '成都']  # 城市列表
    cities = ['北京', '上海', '广州']  # 城市列表

    result_queue = Queue()
    loader = LoadPriceHIG()

    try:
        # 打开 8 个 tab 页面（4 个城市，每个城市 2 个 tab）
        # loader.open_tabs(8)
        loader.open_tabs(4)


        # 多线程处理每个城市的数据
        threads = []
        for city in cities:
            thread = Thread(target=process_city, args=(loader, city, result_queue))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 打印结果
        while not result_queue.empty():
            print(result_queue.get())

    finally:
        # 关闭浏览器
        loader.close_browser()


if __name__ == '__main__':
    main()