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
import json
import time
from DrissionPage import ChromiumPage
from util.HotelDatabase import HotelDatabase
import logging

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
    # 初始化浏览器和数据库
    page = ChromiumPage()
    db = HotelDatabase()

    try:
        # 打开目标页面
        # page.listen.start('apis.ihg.com.cn/hotels/v3/profiles')  # Start the listener, specifying to capture data packets containing this text
        page.listen.start('https://apis.ihg.com.cn/hotels/v3/profiles/NKGRS/details?fieldset=brandInfo,location,reviews,profile,address,parking,media,policies,facilities,badges,stripes,room,renovations,tax,marketing,greenEngage,renovationAlerts.active&brandCode=HIEX&ihg-language=zh-cn')  # Start the listener, specifying to capture data packets containing this text
        url = 'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8D%97%E4%BA%AC,%20%E6%B1%9F%E8%8B%8F,%20%E4%B8%AD%E5%9B%BD&qPt=CASH&qCiD=30&qCoD=31&qCiMy=042025&qCoMy=042025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&srb_u=1&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=30&qRdU=mi&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1'
        page.get(url)

        resp = page.listen.wait()
        hotel = resp.response.body['hotelContent'][0]

        """
         将响应数据的 "hotelContent.hotelCode"、"hotelContent.brandInfo.brandCode"、"hotelContent.brandInfo.brandName"、"hotelContent.profile.name"、
        "hotelContent.profile.latLong.longitude"、"hotelContent.profile.latLong.latitude"、"hotelContent.address.translatedMainAddress.line1.value"、
        "hotelContent.profile.entityOpenDate"属性值取出，使用现有的HotelDatabase.py文件中的insert_data方法存到数据库的hotel表中，分别对应hotel表的
        hotelcode、brandcode、enname、name、longitude、latitude、address、startyear列中。
        {'hotelcode': 'NKGRS', 'brandcode': 'HIEX', 'enname': 'Holiday Inn Express', 'name': '南京滨江智选假日酒店', 'longitude': '118.73766', 'latitude': '32.09012', 'address': '江苏省南京市鼓楼区公共路18号', 'startyear': '2024-08-13'}
        """
        hotel_data = {
                'hotelcode': hotel.get('hotelCode'),
                'brandcode': hotel.get('brandInfo').get('brandCode'),
                'enname': hotel.get('brandInfo').get('brandName'),
                'name': hotel.get('profile').get('name')[0].get('value'),
                'longitude': hotel.get('profile').get('latLong').get('longitude'),
                'latitude': hotel.get('profile').get('latLong').get('latitude'),
                'address': hotel.get('address').get('translatedMainAddress').get('line1')[0].get('value'),
                'startyear': hotel.get('profile').get('entityOpenDate')
            }
        db.insert_data('hotel', hotel_data)
        logging.info(f"捕获到请求：{hotel_data}")
    except Exception as e:
        print(f"运行过程中发生错误：{e}")
    finally:
        # 关闭浏览器和数据库连接
        page.quit()
        db.close()

if __name__ == '__main__':
    main()