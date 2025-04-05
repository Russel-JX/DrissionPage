"""
获取IHG酒店元数据。
包括：具体酒店名、酒店的集团code/子品牌code/酒店code、经纬度、酒店细节等
过程：
    1.根据city表中城市数据，逐个向官方请求。
    如qDest=北京亚运村，请求北京城市的酒店列表
    https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false
        1.1获取每个酒店的详情页信息。如果有一个响应的hotel.address.city是北京，则此城市有该酒店，更新city记录的hotelavailable=true。(以后爬取城市具体酒店的价格信息时，只爬取该城市hotelavailable=true的酒店)。
        否则，该城市无任何此集团酒店。
        https://apis.ihg.com.cn/hotels/v1/profiles/PEGHC/details?fieldset=brandInfo,location,reviews,profile,address,parking,media,policies,facilities,badges,stripes,room,renovations,tax,marketing,greenEngage,renovationAlerts.active&brandCode=ICON&ihg-language=zh-cn
"""
import time
from DrissionPage import ChromiumPage
from DrissionPage import Chromium, ChromiumOptions
from util.HotelDatabase import HotelDatabase
import logging
import traceback
import re
from datetime import datetime, timedelta
from util.StrUtil import StrUtil
import json

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

CITIES = ['忻州市','上海','淮安']  # 城市列表
# CITIES = ['北京', '上海', '广州', '深圳', '南京', '武汉', '成都', '杭州', '大连', '淮安', '扬州', 'xx', '无锡市', '泉州市', '西湖'] 


"""
频率：可以很长，如1周，1个月，半年。1次。
普通:18-20s
无图无声：18-20s
使用来宾模式:20-22s
耗时统计：
1个城市，40秒。总共342个城市，耗时约4小时。50个城市，耗时约1小时。
多个城市平均每个15秒。总共342个城市，耗时约1.5小时。50个城市，耗时约13分钟。
注：python策划给你续运行时，自动或主动关闭屏幕显示，不影响程序运行。
"""
"""
洲际有的城市，因为没有酒店或本市洲际很少，页面展示包含了周边城市的洲际酒店。要排除这种，来避免重复数据。
对meta数据收集，可以存页面返回的周边城市酒店，但用额外字段local表示(1：本市，0：周边)：
	1.只收集市级酒店(因为市级酒店包括了县级市酒店，县级市不再次收集)
	2.对市级没有酒店或因为本市很少返回了部分周边酒店的判断：当页面返回的酒店数量<=20时，都存入DB，用local字段区分。否则只存入本市的酒店。
    以后在UI可以区分显示。如镇江有1,2,3家洲际酒店，横线下方再展示事先存DB的南京、扬州等地的酒店。
    目的是为了用户可以扩大选择。
对酒店价格的收集：事先在meta表查询，没有酒店的城市（local=0），直接并不进行收集
"""
def main():
    start_time = time.time()
    
    # 创建配置对象（默认从 ini 文件中读取配置）
    co = ChromiumOptions()
    # 设置不加载图片、静音。这个基本没效果
    co.no_imgs(True).mute(True)
    # 设置启动时最大化
    co.set_argument('--start-maximized')
    # 无沙盒模式.在某些 Linux 环境下，Chrome 无头模式可能会受到沙盒限制，导致无法正常启动。禁用沙盒可以解决这个问题
    co.set_argument('--no-sandbox')  
    # 使用来宾模式打开浏览器。无浏览历史、没有书签、无登录、无浏览器设置
    co.set_argument('--guest')
     # 禁用自动化标识
    co.set_argument('--disable-blink-features=AutomationControlled')

    # 无头模式必须结合 User-Agent一起用。否则，虽然浏览器没有打开，但导致页面基本内容没有加载，洲际应该有js控制：让没显示特定html，就不加载数据的请求，拿不到任何数据！
    co.headless()
    # 修改 User-Agent.可以解决无头模式的反扒问题！
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    # 以该配置创建页面对象
    page = ChromiumPage(addr_or_opts=co)

    # 初始化浏览器和数据库
    # page = ChromiumPage()
    db = HotelDatabase()
    pricedate = datetime.today()
    su = StrUtil()

    try:
        # 从 city 表中查询所有城市名称
        query_result = db.query_data('city', conditions=None)  # 假设 city 表中有 name 列
        cities = [row['name'] for row in query_result]  # 提取 name 列的值
        # logging.info(f"从数据库中查询到的城市列表：{cities}")
        #测试用城市列表
        # cities = CITIES
        for city in cities:
            inner_start_time =  time.time()
            # 1个城市有效请求数
            count = 0

            params = getHIGMetaParams(city, pricedate)
            # 监听网络中所有满足的url请求。因为IHG的酒店详情页url有时是https://apis.ihg.com.cn/hotels/v3/profiles/，有时是https://apis.ihg.com.cn/hotels/v1/profiles/，有时是https://apis.ihg.com.cn/hotels/*/profiles/，所以需要监听所有满足的url请求。
            # https://github.com/Russel-JX/DrissionPage/blob/master/docs_en/ChromiumPage/network_listener.md  监听网络数据
            page.listen.start(targets='https://apis.ihg.com.cn/hotels/.*/profiles/', is_regex=True)

            # 只监听网络中1个URL
            # page.listen.start('https://apis.ihg.com.cn/hotels/v3/profiles/NKGRS/details?fieldset=brandInfo,location,reviews,profile,address,parking,media,policies,facilities,badges,stripes,room,renovations,tax,marketing,greenEngage,renovationAlerts.active&brandCode=HIEX&ihg-language=zh-cn') 
            # 浏览器中的URL。注：浏览器中的URL，可对应多个网络的url
            # url = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8D%97%E4%BA%AC,%20%E6%B1%9F%E8%8B%8F,%20%E4%B8%AD%E5%9B%BD&qPt=CASH&qCiD=30&qCoD=31&qCiMy=042025&qCoMy=042025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=30&qRdU=mi&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
            # 延安无酒店case
            url = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E4%B8%AD%E5%9B%BD%E9%99%95%E8%A5%BF%E7%9C%81%E5%BB%B6%E5%AE%89%E5%B8%82&qPt=POINTS_CASH&qCiD=30&qCoD=31&qCiMy=042025&qCoMy=042025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=IVANI&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
            
            url = su.replace_URLParam(url, params)
            logging.info(f"{city}请求的url是：{url}")
            page.get(url)
            
            """
            调试chrome浏览器的无头模式
            """
            # # 获取页面标题。无图模式下，"上海页面把标题是：Access Denied"
            # logging.info(f"{city}页面把标题是：{page.title}")
            # # 抓取屏幕截图来查看浏览器是否成功加载了页面。
            # page.get_screenshot('screenshot.png')

            try:
            
                """
                V1和V3的json数据格式区别：前者以"hotelInfo"开头且"hotelInfo"是对象，后者以"hotelContent"开头，"hotelContent"是长度是1的数组。
                V1的json数据格式:
                "hotelInfo.brandInfo.mnemonic"、"hotelInfo.brandInfo.brandCode"、"hotelInfo.brandInfo.brandName"、"hotelInfo.profile.name"、
                "hotelInfo.profile.latLong.longitude"、"hotelInfo.profile.latLong.latitude"、"hotelInfo.address.street1"、
                "hotelInfo.address.city"、
                "hotelInfo.profile.entityOpenDate"
                V3的json数据格式:
                将响应数据的 "hotelContent.hotelCode"、"hotelContent.brandInfo.brandCode"、"hotelContent.brandInfo.brandName"、"hotelContent.profile.name[0].value"、
                "hotelContent.profile.latLong.longitude"、"hotelContent.profile.latLong.latitude"、"hotelContent.address.translatedMainAddress.line1[0].value"、
                "hotelContent.address.translatedMainAddress.city[0].value"、
                "hotelContent.profile.entityOpenDate"属性值取出，使用现有的HotelDatabase.py文件中的insert_data方法存到数据库的hotel表中，分别对应hotel表的
                hotelcode、brandcode、enname、name、longitude、latitude、address、city、startyear列中。
                {'hotelcode': 'NKGRS', 'brandcode': 'HIEX', 'enname': 'Holiday Inn Express', 'name': '南京滨江智选假日酒店', 'longitude': '118.73766', 'latitude': '32.09012', 'address': '江苏省南京市鼓楼区公共路18号', 'startyear': '2024-08-13'}
                """
                # 将生成器转换为列表。每个数据包最多等3秒，必须结束监听返回数据。不这样做的话，会导致页面一直在监听，如果页面自动刷新则会导致重复数据。
                # TODO这里还会出现重复url的问题。比如：同一个酒店的详情页url会被多次请求，导致数据重复。
                packets = list(page.listen.steps(count=None, timeout=3, gap=1))  
                # packets = list(page.listen.wait(fit_count=False))  

                logging.info(f"{city}捕获到总请求数：{len(packets)}")
                # 注：城市无酒店的耗时比有酒店的长一点
                if len(packets) == 0:
                    logging.info(f"{city}无洲际酒店meta数据")
                    continue
                fisrtPacketUrl = packets[0].url

                # 定义正则表达式。https://apis.ihg.com.cn/hotels/ 和 /profiles 之间的部分
                pattern = r'https://apis\.ihg\.com\.cn/hotels/(.*)/profiles/'
                # 使用正则表达式提取值
                urlVersion = re.match(pattern, fisrtPacketUrl).group(1)
                logging.info(f"{city}请求版本是：{urlVersion}")

                # 遍历所有具体酒店细节的请求结果
                for packet in packets:
                    # logging.info(f"捕获到请求：{packet.url}")

                    if urlVersion == 'v1':
                        hotel = packet.response.body['hotelInfo']

                        hotel_data = {
                        'groupcode': 'IHG',
                        'groupname': '洲际',
                        'brandname': hotel.get('brandInfo', {}).get('brandName', ''),
                        'hotelcode': hotel.get('brandInfo', {}).get('mnemonic', ''),
                        'brandcode': hotel.get('brandInfo', {}).get('brandCode', ''),
                        'enname': hotel.get('brandInfo', {}).get('brandName', ''),
                        'name': hotel.get('profile', {}).get('name', ''),
                        'longitude': hotel.get('profile', {}).get('latLong', {}).get('longitude'),
                        'latitude': hotel.get('profile', {}).get('latLong', {}).get('latitude'),
                        'address': hotel.get('address', {}).get('street1', ''),
                        'city': city,
                        'startyear': hotel.get('profile', {}).get('entityOpenDate'),
                        'pic': hotel.get('profile', {}).get('primaryImageUrl', {}).get('originalUrl', ''),
                        'note': urlVersion
                        }
                        if len(packets)>20 and city.find(hotel.get('address', {}).get('city', '')) == -1:
                            continue
                        else:
                            count = count+1
                            local = city.find(hotel.get('address', {}).get('city', ''))
                            if local != -1:
                                hotel_data['local'] = 1
                            else:
                                hotel_data['local'] = 0
                            # logging.info(f"有效数据：{hotel_data}")
                            db.insert_data('hotel', hotel_data)
                    elif urlVersion == 'v3':
                        hotel = packet.response.body['hotelContent'][0]
                        hotel_data = {
                        'groupcode': 'IHG',
                        'groupname': '洲际',
                        'brandname': hotel.get('brandInfo', {}).get('brandName', ''),
                        'hotelcode': hotel.get('hotelCode', {}, ''),
                        'brandcode': hotel.get('brandInfo', {}).get('brandCode', ''),
                        'enname': hotel.get('brandInfo', {}).get('brandName', ''),
                        'name': hotel.get('profile', {}).get('name', {})[0].get('value', ''),
                        'longitude': hotel.get('profile', {}).get('latLong', {}).get('longitude'),
                        'latitude': hotel.get('profile', {}).get('latLong', {}).get('latitude'),
                        'address': hotel.get('address', {}).get('translatedMainAddress', {}).get('line1', {})[0].get('value', ''),
                        'city': city,
                        'startyear': hotel.get('profile', {}).get('entityOpenDate'),
                        'pic': hotel.get('profile', {}).get('primaryImageUrl', {}).get('originalUrl', ''),
                        'note': urlVersion
                        }
                        if len(packets)>20 and city.find(hotel.get('address', {}).get('translatedMainAddress', {}).get('city', '')[0].get('value')) == -1 :
                            continue
                        else:
                            count = count+1
                            local = city.find(hotel.get('address', {}).get('translatedMainAddress', {}).get('city', '')[0].get('value'))
                            if local != -1:
                                hotel_data['local'] = 1
                            else:
                                hotel_data['local'] = 0
                            # logging.info(f"有效数据：{hotel_data}")
                            db.insert_data('hotel', hotel_data) 
                    else:
                        logging.error(f"{city}未知的URL版本：{urlVersion}")
                        continue    
                # 1个城市的所有请求处理完后，清空监听
                page.listen.stop() 
                inner_end_time =  time.time()
                logging.info(f"{city}有效请求数：{count}，耗时：{inner_end_time - inner_start_time:.2f} 秒)")
            except Exception as e:
                print(f"内部{city}运行过程中发生错误：{e}")
                logging.error(f"内部{city}运行过程中发生错误：{e}")
                logging.error("内部Stack trace:\n%s", traceback.format_exc()) 
    except Exception as e:
        print(f"{city}运行过程中发生错误：{e}")
        logging.error(f"{city}运行过程中发生错误：{e}")
        logging.error("Stack trace:\n%s", traceback.format_exc())  # 使用 traceback.format_exc() 获取堆栈信息
    finally:
        end_time =  time.time()
        logging.info(f"所有城市，耗时：{end_time - start_time:.2f} 秒)")
        # 关闭浏览器和数据库连接
        page.quit()
        db.close()

def getHIGMetaParams(city, pricedate):
        """
        构造 URL 参数
        """
        params = {
            'qDest': city,
            'qCiD': f"{pricedate.day:02d}",
            'qCoD': f"{(pricedate + timedelta(days=1)).day:02d}",
            'qCiMy': f"{(pricedate - timedelta(days=30)).month:02d}20{(pricedate - timedelta(days=30)).year % 100}",
            'qCoMy': f"{(pricedate - timedelta(days=30)).month:02d}20{(pricedate - timedelta(days=30)).year % 100}"
        }
        return params

if __name__ == '__main__':
    main()