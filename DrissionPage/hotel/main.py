from threading import Thread
from queue import Queue
from LoadPriceHIG import LoadPriceHIG
from datetime import datetime, timedelta
from util.StrUtil import StrUtil
import time


def process_city(loader, city, result_queue):
    """
    处理单个城市的数据
    """
    try:
        pricedate = datetime.today()
        version = datetime.now().strftime('%Y-%m-%d %H')

        for i in range(2):  # 爬取两天的数据
            # 构造 URL
            params = loader.getHIGParams(city, pricedate)
            su = StrUtil()
            # 价格信息URL
            priceURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false'
            # 积分信息URL
            pointsURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=POINTS&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=IVANI&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
            
            priceURL = su.replace_URLParam(priceURL, params)
            pointsURL = su.replace_URLParam(pointsURL, params)
            # priceURL = su.replace_URLParam('https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qPt=CASH', params)
            # pointsURL = su.replace_URLParam('https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qPt=POINTS', params)

            # 加载价格和积分数据
            hotel_price_list = loader.loadData(priceURL, city, 'price', pricedate)
            hotel_points_list = loader.loadData(pointsURL, city, 'points', pricedate)

            # 合并数据
            hotel_list = loader.merge_hotel_data(hotel_price_list, hotel_points_list)

            # 保存到数据库
            for hotel in hotel_list:
                hotel['version'] = version
                hotel['pricedate'] = pricedate
                loader.db.insert_data('hotelprice', hotel)

            result_queue.put(f"城市 {city} {pricedate} 数据爬取完成")
            pricedate += timedelta(days=1)

    except Exception as e:
        result_queue.put(f"城市 {city} 数据爬取失败：{e}")


def main():
    cities = ['北京', '上海', '广州']  # 城市列表
    result_queue = Queue()
    loader = LoadPriceHIG()

    

    try:
        # 为每个城市打开一个 tab 页面
        loader.open_tabs_for_cities(cities)

        # 切换到每个 tab 页面一次，确保页面渲染完成
        loader.switch_to_all_tabs()

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