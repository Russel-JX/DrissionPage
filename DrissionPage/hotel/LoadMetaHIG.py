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
from util.HotelDatabase import HotelDatabase
import logging
import traceback
import re

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

def main():
    start_time = time.time()
    # 初始化浏览器和数据库
    page = ChromiumPage()
    db = HotelDatabase()

    try:
        # 监听网络中所有满足的url请求。因为IHG的酒店详情页url有时是https://apis.ihg.com.cn/hotels/v3/profiles/，有时是https://apis.ihg.com.cn/hotels/v1/profiles/，有时是https://apis.ihg.com.cn/hotels/*/profiles/，所以需要监听所有满足的url请求。
        # https://github.com/Russel-JX/DrissionPage/blob/master/docs_en/ChromiumPage/network_listener.md  监听网络数据
        page.listen.start(targets='https://apis.ihg.com.cn/hotels/.*/profiles/', is_regex=True)

        # 只监听网络中1个URL
        # page.listen.start('https://apis.ihg.com.cn/hotels/v3/profiles/NKGRS/details?fieldset=brandInfo,location,reviews,profile,address,parking,media,policies,facilities,badges,stripes,room,renovations,tax,marketing,greenEngage,renovationAlerts.active&brandCode=HIEX&ihg-language=zh-cn') 
        # 浏览器中的URL。注：浏览器中的URL，可对应多个网络的url
        url = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8D%97%E4%BA%AC,%20%E6%B1%9F%E8%8B%8F,%20%E4%B8%AD%E5%9B%BD&qPt=CASH&qCiD=30&qCoD=31&qCiMy=042025&qCoMy=042025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=30&qRdU=mi&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
        page.get(url)

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
        logging.info(f"捕获到总请求数：{len(packets)}")
        fisrtPacketUrl = packets[0].url

        # 定义正则表达式。https://apis.ihg.com.cn/hotels/ 和 /profiles 之间的部分
        pattern = r'https://apis\.ihg\.com\.cn/hotels/(.*)/profiles/'
        # 使用正则表达式提取值
        urlVersion = re.match(pattern, fisrtPacketUrl).group(1)
        logging.info(f"请求版本是：{urlVersion}")

        # 遍历所有具体酒店细节的请求结果
        for packet in packets:
            # logging.info(f"捕获到请求：{packet.url}")
            if urlVersion == 'v1':
                hotel = packet.response.body['hotelInfo']
                hotel_data = {
                'groupcode': 'IHG',
                'groupname': '洲际',
                'brandname': hotel.get('brandInfo').get('brandName'),
                'hotelcode': hotel.get('brandInfo').get('mnemonic'),
                'brandcode': hotel.get('brandInfo').get('brandCode'),
                'enname': hotel.get('brandInfo').get('brandName'),
                'name': hotel.get('profile').get('name'),
                'longitude': hotel.get('profile').get('latLong').get('longitude'),
                'latitude': hotel.get('profile').get('latLong').get('latitude'),
                'address': hotel.get('address').get('street1'),
                'city': hotel.get('address').get('city'),
                'startyear': hotel.get('profile').get('entityOpenDate'),
                'pic': hotel.get('profile').get('primaryImageUrl').get('originalUrl'),
                'note': urlVersion
                }
            elif urlVersion == 'v3':
                hotel = packet.response.body['hotelContent'][0]
                hotel_data = {
                'groupcode': 'IHG',
                'groupname': '洲际',
                'brandname': hotel.get('brandInfo').get('brandName'),
                'hotelcode': hotel.get('hotelCode'),
                'brandcode': hotel.get('brandInfo').get('brandCode'),
                'enname': hotel.get('brandInfo').get('brandName'),
                'name': hotel.get('profile').get('name')[0].get('value'),
                'longitude': hotel.get('profile').get('latLong').get('longitude'),
                'latitude': hotel.get('profile').get('latLong').get('latitude'),
                'address': hotel.get('address').get('translatedMainAddress').get('line1')[0].get('value'),
                'city': hotel.get('address').get('translatedMainAddress').get('city')[0].get('value'),
                'startyear': hotel.get('profile').get('entityOpenDate'),
                'pic': hotel.get('profile').get('primaryImageUrl').get('originalUrl'),
                'note': urlVersion
                }
            else:
                logging.error(f"未知的URL版本：{urlVersion}")
                continue  
            db.insert_data('hotel', hotel_data)
            # logging.info(f"有效数据：{hotel_data}")   
    except Exception as e:
        print(f"运行过程中发生错误：{e}")
        logging.error(f"运行过程中发生错误：{e}")
        logging.error("Stack trace:\n%s", traceback.format_exc())  # 使用 traceback.format_exc() 获取堆栈信息
    finally:
        end_time =  time.time()
        logging.info(f"总请求数：{len(packets)}，耗时：{end_time - start_time:.2f} 秒)")
        # 关闭浏览器和数据库连接
        page.quit()
        db.close()

if __name__ == '__main__':
    main()