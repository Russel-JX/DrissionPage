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

async def monitor_xhr_requests(page, db):
    """
    监听并处理 XHR 请求
    """
    async def intercept_request(request):
        if request.resourceType == 'xhr' and request.url.startswith('https://apis.ihg.com.cn/hotels/v3/profiles'):
            print(f"捕获到 XHR 请求：{request.url}")
            response = await request.response()
            if response:
                try:
                    # 解析 JSON 响应数据
                    data = await response.json()
                    # TODO 暂时不处理数据
                    # process_hotel_data(data, db)
                except Exception as e:
                    print(f"处理 XHR 请求数据时发生错误：{e}")

    # 设置拦截器
    # page.browser.set_request_interception(True)
    #page.browser.on('request', intercept_request)
    
    await page.set_request_interception(True)
    page.on('request', intercept_request)
    


def process_hotel_data(data, db):
    """
    处理酒店数据并存入数据库
    """
    try:
        for hotel in data.get('hotelContent', []):
            hotel_data = {
                'hotelcode': hotel.get('hotelCode'),
                'brandcode': hotel.get('brandInfo', {}).get('brandCode'),
                'enname': hotel.get('brandInfo', {}).get('brandName'),
                'name': hotel.get('profile', {}).get('name', [{}])[0].get('value'),
                'longitude': hotel.get('profile', {}).get('latLong', {}).get('longitude'),
                'latitude': hotel.get('profile', {}).get('latLong', {}).get('latitude'),
                'address': hotel.get('address', {}).get('translatedMainAddress', {}).get('line1', [{}])[0].get('value'),
                'startyear': hotel.get('profile', {}).get('entityOpenDate')
            }
            # 插入数据到数据库
            db.insert_data('hotel', hotel_data)
            print(f"插入酒店数据：{hotel_data}")
    except Exception as e:
        print(f"处理酒店数据时发生错误：{e}")

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

        # 开始监听 XHR 请求
        # monitor_xhr_requests(page, db)

        resp = page.listen.wait()
        hotel = resp.response.body['hotelContent'][0]
        # print(f"捕获到请求1：{resp}")
        # print(f"捕获到请求2：{json}")
        print(f"捕获到请求2：{hotel['hotelCode']}")
       

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
        print(f"捕获到请求3：{hotel_data}")

        logging.info(f"捕获到请求：{resp}")


        # i = 0
        # for packet in page.listen.steps():
        #     logging.info(f"捕获到 XHR 请求：{packet.url}")
        #     i += 1
        #     if i == 5:
        #         break
        # for _ in range(5):
        #     # page('@rel=next').click()  # Click on the next page
        #     res = page.listen.wait()  # Wait for and capture a data packet
        #     logging.info(f"捕获到 XHR 请求：{res.url}")


        # 模拟页面操作（例如滚动加载更多内容）
        # for _ in range(10):
        #     page.scroll.to_bottom()
        #     time.sleep(2)

    except Exception as e:
        print(f"运行过程中发生错误：{e}")
    finally:
        # 关闭浏览器和数据库连接
        page.quit()
        db.close()

if __name__ == '__main__':
    main()