#爬取具体酒店的一天价格信息
from DrissionPage import ChromiumPage
from pathlib import Path
import time
from util.HotelDatabase import HotelDatabase
from models.hotel_dicts import TABLES

class LoadPriceHIG:
    def __init__(self):
        self.db = HotelDatabase()
    # db = HotelDatabase()

    # # 插入数据到 hotel 表
    # hotel_data = {
    #     'version': '25.03.23 09',
    #     'hotelcode': 'H123',
    #     'name': '上海外滩W酒店',
    #     'groupcode': 'G001',
    #     'brandcode': 'B001',
    #     'groupname': '万豪集团',
    #     'brandname': 'W酒店',
    #     'country': '中国',
    #     'province': '上海',
    #     'city': '上海',
    #     'minpoints': 20000,
    #     'minprice': 1500,
    #     'latitude': 31.2304,
    #     'longitude': 121.4737,
    #     'address': '上海市黄浦区外滩',
    #     'features': '免早,直升套房',
    #     'createtime': '2025-03-23 10:00:00'
    # }
    # db.insert_data('hotel', hotel_data)

    # # 查询 hotel 表数据
    # db.query_data('hotel', {'city': '上海'})

    # # 关闭数据库连接
    # db.close()

    def getHotelInfo(self, city, result_queue):
        print(f'====load数据！====')
        try:
            # 价格信息URL
            priceURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false'
            # 积分信息URL
            pointsURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=POINTS&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=IVANI&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
            
            hotel_price_list = self.loadData(priceURL, 'price')
            hotel_points_list = self.loadData(pointsURL, 'points')
            print(f'====酒店价格数量：{len(hotel_price_list)}，酒店积分数量：{len(hotel_points_list)}====')
            # for index, hotel in enumerate(hotel_price_list):
            #     hotel['name']
            #     self.db.insert_data(TABLES['hotelprice'], hotel)

            # 对具体相同酒店，合并name,price,points信息
            hotel_list = self.merge_hotel_data(hotel_price_list, hotel_points_list)
            # 存DB
            # 数据库连接
            db = HotelDatabase()
            # TODO数据字典，用定义好的TABLES.hotelprice??
            for hotel in hotel_list:
                db.insert_data(TABLES['hotelprice'], hotel) 
            # 关闭数据库连接
            db.close()

            # 将结果存入队列
            result_queue.put(f"城市 {city['name']} 爬取完成")

        except Exception as e:
            print(f"爬取城市 {city['name']} 时发生错误：{e}")
            result_queue.put(f"城市 {city['name']} 爬取失败：{e}")
    
    #合并酒店的价格信息和积分信息
    def merge_hotel_data(self, price_list, points_list):
        """
        合并酒店的价格信息和积分信息
        :param price_list: 包含价格信息的酒店列表
        :param points_list: 包含积分信息的酒店列表
        :return: 合并后的酒店列表
        """
        # 创建一个字典，用于快速查找酒店。key-object形式
        hotel_dict = {}

        # 遍历价格列表，将价格信息存入字典
        for hotel in price_list:
            name = hotel['name']
            if name not in hotel_dict:
                hotel_dict[name] = {
                    'name': name,
                    'minprice': hotel.get('price', ''),
                    'minpoints': ''  # 初始化积分为空
                }
            else:
                hotel_dict[name]['minprice'] = hotel.get('price', '')

        # 遍历积分列表，将积分信息合并到字典中
        for hotel in points_list:
            name = hotel['name']
            if name not in hotel_dict:
                hotel_dict[name] = {
                    'name': name,
                    'minprice': '',  # 初始化价格为空
                    'minpoints': hotel.get('points', '')
                }
            else:
                hotel_dict[name]['minpoints'] = hotel.get('points', '')

        # 将字典转换为列表。[{},{}]形式
        merged_list = list(hotel_dict.values())
        return merged_list


    """
    #2.1 每个城市一个线程。一个线程中：
        # 发起请求，获取酒店列表及价格信息；
        # 发起请求，获取酒店列表及积分信息；
        # 对具体相同酒店，DB记录价格和积分信息。
    """
    def loadData(self, url=None, queryType=None):
        # 当前文件路径
        file_path = Path(__file__)
        start_time = time.time()
        page = ChromiumPage()
        print(f'===={file_path.name}执行开始！====')

        # 打开目标页面，获取所需价格或积分信息
        page.get(url)
        # 下滑到底，获取更多内容
        last_height = 0
        same_count = 0

        for _ in range(30):  # 最多下滑30次
            page.scroll.to_bottom()
            time.sleep(1)  # 减少等待时间

            height = page.run_js('document.body.scrollHeight')
            if height == last_height:
                same_count += 1
                if same_count >= 3:
                    print("滑到底了，停止滚动。")
                    break
            else:
                same_count = 0
                last_height = height
        hotel_list = []
        hotel_data = {
                'name': None,
                'price': None,
                'points': None
            }
        # 获取所有酒店卡片。使用s_eles代替eles，速度从60s提升至12s
        # hotels = page.eles('@class=hotel-card-list-resize ng-star-inserted')
        hotels = page.s_eles('@class=hotel-card-list-resize ng-star-inserted')
        print("======酒店总数======", len(hotels))

        for hotel in hotels:
            # 优先取 brandHotelNameSID，其次 hotelNameSID > span
            name = hotel.ele('@data-slnm-ihg=brandHotelNameSID')
            price = None
            points = None
            if not name:
                name_container = hotel.ele('@data-slnm-ihg=hotelNameSID')
                name = name_container.ele('tag:span') if name_container else None

            # 优先取正常价格，其次判断无房价格提示
            if queryType == 'price':#价格信息
                price = hotel.ele('@class=price') or hotel.ele('@data-testid=noRoomsAvail')
            elif queryType == 'points':#积分信息  data-slnm-ihg="dailyPointsCostSID"  data-testid="noRoomsAvail"
                points = hotel.ele('@data-slnm-ihg=dailyPointsCostSID') or hotel.ele('@data-testid=noRoomsAvail')

            hotel_data['name'] = name.text
            hotel_data['price'] = price.text if price else '' 
            hotel_data['points'] = points.text if points else ''
            hotel_list.append(hotel_data)

            # 打印酒店名、价格信息（注意判空）
            # print(f"酒店名称：{name.text if name else '未知'}, 价格：{price.text if price else '无'}")

        end_time =  time.time()
        return hotel_list
        print(f'===={file_path.name}执行成功完成！耗时 {end_time - start_time:.2f} 秒====')
        page.quit()