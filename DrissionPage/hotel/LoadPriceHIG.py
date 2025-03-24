#爬取具体酒店的一天价格信息
from DrissionPage import ChromiumPage
from pathlib import Path
import time
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
import traceback
import inspect
from util.HotelDatabase import HotelDatabase
from models.hotel_dicts import TABLES
from util.StrUtil import StrUtil


class LoadPriceHIG:
    def __init__(self):
        self.db = HotelDatabase()

    """
    params = {
                'pricedate': '',
                'version': '',
                'qCiD': '',   
                'qCoD': '',   
                'qCiMy': '',  
                'qCoMy': ''
            }   
    """
    def getHIGParams(self, city, pricedate):
        params = {
            'qDest': '', 
            'qCiD': '',   
            'qCoD': '',   
            'qCiMy': '',  
            'qCoMy': ''
        }
        pricedate_text = pricedate.strftime('%Y-%m-%d') # 今天日期2025-03-23
        nextdate = pricedate+timedelta(days=1)
        
        formatted_day = f"{pricedate.day:02d}"  # 当前日期的日，格式化为两位数字
        formatted_nextday = f"{nextdate.day:02d}" # 当前日期的日，格式化为两位数字
        formatted_month = f"{(pricedate - relativedelta(months=1)).month:02d}"
        formatted_year = (pricedate - relativedelta(months=1)).strftime('%y')
        qmonth = f"{formatted_month}20{formatted_year}"  # 2025-03-24转换为 022025 的形式
        params['qDest'] = city
        params['qCiD'] = formatted_day
        params['qCoD'] = formatted_nextday
        params['qCiMy'] = qmonth
        params['qCoMy'] = qmonth
        return params


    """
    查询一个城市下的一个酒店集团下的所有酒店的价格和积分信息

    URL解释
    洲际价格URL。https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false
    洲际积分URL。https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=POINTS&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=IVANI&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1

    整体表示：查询"北京亚运村"位置，现金支付方式，入住日期在2025-04-23号，离开在2025-04-24号的客房价格
    qDest：查询城市。使用Percent-Encoding的URL 编码。对应的是"北京亚运村"
        qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91
    qPt:支付方式。CASH：现金；POINTS：积分
        qPt=CASH
    qCiD:客户入住日期
        qCiD=23
    qCoD:客户离开日期
        qCoD=24
    qCiMy/qCoMy:客户入住/离开的月份和年份。url参数比实际查询的月份小1个月。下面表示：去查3+1=4月份，25年
        qCiMy=032025
        qCoMy=032025
    """
    def getHotelInfo(self, city, result_queue):
        start_time = time.time()
        version = datetime.now().strftime('%Y-%m-%d %H') # 当前日期时间2025-03-23 15
        print(f'===={inspect.currentframe().f_code.co_name}方法load{city} version:{version}城市数据！====')

        try:
            # 价格信息URL
            priceURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false'
            # 积分信息URL
            pointsURL = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=POINTS&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=IVANI&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
            
            pricedate = datetime.today()
            #共用的部分拿出来。如数据库的连接和关闭,共用对象。提升运行速度
            # 数据库连接
            db = HotelDatabase()
            su = StrUtil()
            for i in range(2):#爬取两天的价格和积分信息
                start_day_time = time.time()
                params = self.getHIGParams(city, pricedate)
                print(f'====第{i+1}天，url params：{params})')
                
                priceURL = su.replace_URLParam(priceURL, params)
                pointsURL = su.replace_URLParam(pointsURL, params)
                print(f'====价格url：{priceURL})')
                print(f'====积分url：{pointsURL})')
                # TODO以后尝试把同一城市同一天的请求价格和积分信息放在一起并行的线程中且互相等待，加快速度
                # 即外层还是多个城市对应多个线程跑，这里再新建2个子线程绑定跑
                hotel_price_list = self.loadData(priceURL, city, 'price', pricedate)
                hotel_points_list = self.loadData(pointsURL, city, 'points', pricedate)
                print(f'===={city} {pricedate} 酒店价格数量：{len(hotel_price_list)}，酒店积分数量：{len(hotel_points_list)}====')
                # 对具体相同酒店，合并name,price,points信息
                hotel_list = self.merge_hotel_data(hotel_price_list, hotel_points_list)

                for hotel in hotel_list:
                    hotel['version'] = version
                    hotel['pricedate'] = pricedate
                    db.insert_data('hotelprice', hotel)
                # 将结果存入队列
                result_queue.put(f"城市 {city} 爬取完成")
                end_day_time =  time.time()
                print(f'===={city} {pricedate}耗时 {end_day_time - start_day_time:.2f} 秒====')
                #下一天作为新的pricedate去查价格和积分
                pricedate = pricedate+timedelta(days=1)
            # 关闭数据库连接
            db.close()
            final_time =  time.time()
            print(f'===={city}执行成功完成！总耗时 {final_time - start_time:.2f} 秒====')
        except Exception as e:
            print(f"爬取城市 {city} {pricedate}时发生错误：{e}")
            traceback.print_exc()  # 打印详细的堆栈跟踪信息
            result_queue.put(f"城市 {city} {pricedate}爬取失败：{e}")
    
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
                    'minprice': hotel.get('price', -1),
                    'minpoints': -1  # 初始化积分为-1，表示无房或不能用积分
                }
            else:
                hotel_dict[name]['minprice'] = hotel.get('price', -1)

        # 遍历积分列表，将积分信息合并到字典中
        for hotel in points_list:
            name = hotel['name']
            if name not in hotel_dict:
                hotel_dict[name] = {
                    'name': name,
                    'minprice': -1,  # 初始化现金价格为-1，表示无房或不能用现金
                    'minpoints': hotel.get('points', -1),
                    # 'minpoints': hotel.get('points') if isinstance(hotel.get('points'), (int, float)) else -1
                }
            else:
                hotel_dict[name]['minpoints'] = hotel.get('points', -1)

        # 将字典转换为列表。[{},{}]形式
        merged_list = list(hotel_dict.values())
        return merged_list


    """
    #2.1 每个城市一个线程。一个线程中：
        # 发起请求，获取酒店列表及价格信息；
        # 发起请求，获取酒店列表及积分信息；
        # 对具体相同酒店，DB记录价格和积分信息。
    """
    def loadData(self, url=None, city=None, queryType=None, pricedate=None):
        # 当前文件路径
        file_path = Path(__file__)
        start_time = time.time()
        page = ChromiumPage()
        print(f'===={file_path.name}.{inspect.currentframe().f_code.co_name}执行{city}的{queryType}的{pricedate}开始！====')

        # 打开目标页面，获取所需价格或积分信息
        page.get(url)
        # page.get(url, timeout=30)
        # 确保页面完全加载
        # page.wait.load(timeout=10)  

        # 确保页面完全加载
        # try:
        #     page.wait_appear('body', timeout=10)  # 等待 body 元素加载完成
        # except Exception as e:
        #     print(f"页面加载超时或发生错误：{e}")
        #     traceback.print_exc()  # 打印详细的堆栈跟踪信息
        #     return []   

        # 下滑到底，获取更多内容
        last_height = 0
        same_count = 0

        """
        先固定向下滑动几次，让页面完全加载完。如果连续3次，都划不动了，则表示页面到底，不要再划了。
        假设每次向下滑动后，页面都变长5，页面总长度15.
        执行过程：
        第几次滑动      height      last_height             same_count
        1               5           0(5!=0)->5              0->0
        2               10          5(10!=5)->10            0->0
        3               15          10(15!=10)->15          0->0
        4               15          15(15==15)              0->0+1=1(第一次划不动)
        5               15          15(15==15)              1->1+1=2(第二次划不动)
        6               15          15(15==15)              2->2+1=3(连续3次划不动了，即至少等了3秒，下面都没新内容，则到底了)
        """
        for _ in range(15):  # 固定下滑次数，保证页面数据完全加载完。这里下滑15次
            page.scroll.to_bottom()
            time.sleep(1)  # 睡1秒，等下下方新页面内容加载

            #TODO 同时处理2个城市时，有1个城市查询price老是挂了，导致此城市无任何数据。
            # 可能是因为这里的height获取不到，导致一直下滑。
            height = page.run_js('document.body.scrollHeight')#获取网页文档 整个内容的高度，包括当前视口之外不可见的部分
            if height == last_height:
                same_count += 1
                if same_count >= 3:
                    print("{city}的{queryType}的{pricedate}滑到底了，停止滚动。（连续3次，往下滑不动了）")
                    break
            else:
                same_count = 0
                last_height = height
        hotel_list = []
        # 获取所有酒店卡片。使用s_eles代替eles，速度从60s提升至12s
        # hotels = page.eles('@class=hotel-card-list-resize ng-star-inserted')
        hotels = page.s_eles('@class=hotel-card-list-resize ng-star-inserted')
        print(f"======{city}的{queryType} {pricedate}酒店总数======", len(hotels))
        for hotel in hotels:
            hotel_data = {
                'name': '',
                'price': -1,
                'points': -1
            }
            name = ''
            price = -1
            points = -1
            # 优先取 brandHotelNameSID，其次 hotelNameSID > span
            name_container = hotel.ele('@data-slnm-ihg=brandHotelNameSID')
            name = name_container.text if name_container else ''
            if not name_container:
                name_container = hotel.ele('@data-slnm-ihg=hotelNameSID')
                name = name_container.ele('tag:span').text if name_container else ''

            # 优先取正常价格，其次判断无房价格提示
            if queryType == 'price':#价格信息。
                #价格中会返回"1,415 CNY"，要去掉" CNY"。因为<div _ngcontent-ng-c3430809455="" class="price modal-view" data-slnm-ihg="hotelPirceSID"> 1,415 <span _ngcontent-ng-c3430809455="" class="display-n" data-slnm-ihg="currencySID">CNY</span></div>
                price_div = hotel.ele('@data-slnm-ihg=hotelPirceSID')
                if price_div:#有房价格"1,415 CNY"
                    price_text = price_div.text.strip() if price_div else -1
                    # 去掉 CNY（或者任何 span 的内容）
                    currency = price_div.ele('tag:span')
                    if currency:
                        price = price_text.replace(currency.text, '').strip()
                        #去掉数字中间的逗号。18,000->18000
                        price = int(price.replace(',', ''))
                elif hotel.ele('@data-testid=noRoomsAvail'):#无房价格默认为-1
                    price = -1
                # print(f"酒店名称：{name if name else '未知'}, 价格：{price if price else '无'}")
            elif queryType == 'points':#积分信息。noRoomsAvail则无房，返回默认-1  data-slnm-ihg="dailyPointsCostSID"  data-testid="noRoomsAvail"。
                points_div = hotel.ele('@data-slnm-ihg=dailyPointsCostSID')
                if points_div:
                    points = points_div.text.strip() if points_div else -1
                    #去掉数字中间的逗号。18,000->18000
                    points = int(points.replace(',', ''))
                elif hotel.ele('@data-testid=noRoomsAvail'):#无房价格默认为-1
                    points = -1
                # print(f"酒店名称：{name if name else '未知'}, 积分：{points if points else '无'}")

            hotel_data['name'] = name
            hotel_data['price'] = price if price else -1 
            hotel_data['points'] = points if points else -1
            hotel_list.append(hotel_data)
        end_time =  time.time()
        print(f'===={file_path.name} {city}的{queryType}的{pricedate}执行成功完成！耗时 {end_time - start_time:.2f} 秒====')
        page.quit()
        return hotel_list
