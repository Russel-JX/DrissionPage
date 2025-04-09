from threading import Thread, Semaphore, Lock
from queue import Queue
from datetime import datetime, timedelta
from util.StrUtil import StrUtil
from util.HotelDatabase import HotelDatabase
from util.Common import setup_logging
from DrissionPage import ChromiumPage, ChromiumOptions
import logging
import time
import sys
import traceback

# 配置日志
setup_logging()

#常量定义
MAX_DAYS_COUNT = 365  #请求的总天数
CITIES = ['北京']  # 城市列表
# CITIES = ['上海'] 
# CITIES = ['北京', '上海', '广州'] 
# CITIES = ['北京', '上海', '广州', '深圳', '南京', '武汉', '成都', '杭州'] 

class LoadPriceHIG:
    def __init__(self):
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
        # 无头模式，不需要占用焦点。用户可以同时操作其他任何动作。且自动化操作页面时，也不需要获取页面焦点，脚本会自动操作页面。
        co.headless()
        # 修改 User-Agent.可以解决无头模式的反扒问题！
        co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        # co.set_argument('--user-agent=Edg/91.0.864.59')
        # 设置调试端口9230、指定edge浏览器路径
        # co.set_browser_path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')  # 明确设置路径
        # co.set_argument('--remote-debugging-port=9230')  

        # 以该配置创建页面对象
        self.page = ChromiumPage(addr_or_opts=co)
        
        # self.page = ChromiumPage()  # 创建一个全局的浏览器实例
        self.db = HotelDatabase()  # 数据库实例

    
    def getHIGParams(self, city, pricedate):
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
    
    """
    25.04.06因为简化成最多2个tab(2个城市的price tab+points tab)同时在跑，2个tab切换，且是独立线程，问题不大。
    DrissionPage并不提供切换标签页的功能，而是通过get_tab()或者new_tab()方法来获取指定的标签页对象进行操作。

    tab的一些功能：
    https://github.com/Russel-JX/DrissionPage/blob/master/docs_en/ChromiumPage/tab_operation.md
    tab = page.new_tab()  # Create a new tab and get the tab object

    tab.get('https://www.baidu.com')  # Operate the tab using the tab object
    tab = page.get_tab(page.latest_tab)  # Get the specified tab object
    page.tabs_count 返回选项卡的数量。
    page.tabs 列表形式返回所有选项卡 ID
    tab_id = page.find_tabs(url='baidu.com')  查找符合指定条件的标签页
    tab.set.activate()  激活Tab对象
    page.set.activate()  激活Page对象。
    """
    def loadData(self, city, pricedate, url, queryType):
        """
        在指定的 tab 页面中加载数据
        """
        try:
            self.page.get(url)  # 打开目标页面

            # 滚动页面，确保内容加载完全
            last_height = 0
            same_count = 0
            scroll_height_delta = 0
            scroll_end_max_count = 3
            
            # 调试用
            # croll_count = 0
            # effecttive_scroll_count = 0
            """
            城市下，价格记录丢失原因找到
            1.tab.scroll.to_bottom() 1次就滑到底了，中间的酒店元素没来得及渲染；
            2.tab.run_js('document.body.scrollHeight') js代码获取的总高度不正确总返回None，js能执行，给的js代码不对。
            导致按照代码逻辑4次下滑中，第一次直接滑到底，后面3次下滑每次if height == last_height:都是None==None，3次后直接结束
            """
            # scroll_start_time = time()
            # scroll_timeout = 20  # 设置滚动操作的超时时间为 20 秒
            for _ in range(25):  # 最多滚动 25 次结束，连续scroll_end_max_count次滚不动也算结束
                # self._activate_all_tabs() #无头模式下，无需获取页面焦点。因为脚本会自动操作页面。
                # if time() - scroll_start_time > scroll_timeout:
                #     logging.warning("！！！滚动操作超时，停止滚动！！！")
                #     break
                """
                https://drissionpage.cn/browser_control/ele_operation  元素交互，见元素滚动
                tab.scroll.to_bottom() 每次一下子滚到tab页底部，页面来不及渲染，导致数据丢失
                tab.scroll.to_location(300, scroll_height_delta) 每次向下滚动固定距离，保证页面渲染完成
                """
                # tab.scroll.to_bottom()
                # tab.scroll.to_half()
                scroll_height_delta = scroll_height_delta+1500
                # 当页面刷新导致 页面上下文丢失时，to_location方法会无限等待页面滚动，而等不到，导致脚本卡死。怎么解决？
                self.page.scroll.to_location(300, scroll_height_delta)
                # scroll_count = scroll_count+1
                
                # #测试是否能返回值。输出：JavaScript 测试返回值：42   说明js代码可以运行
                # result = tab.run_js('return 42;')  
                # logging.info(f"JavaScript 测试返回值：{result}") 
                
                time.sleep(1)  # 等待 1 秒，确保刚滚下的页面加载完成

                # 每次获取页面总高度，包括当前可见部分和不可见的滚动区域。
                # 注： tab.run_js('return document.body.scrollHeight;') js代码有return才能有返回值，否则拿不到变量值(返回None)！
                # tab.run_js('document.body.scrollHeight;')  # 直接运行js代码，返回None
                height = self.page.run_js('return document.body.scrollHeight;') # 总高度= 视图高度+滚动高度。如视图高度2None。13768, 14052
                viewHeight = self.page.run_js('return document.documentElement.clientHeight;') # 视图高度。固定840
                # logging.info(f"Tab {tab_index}  {city} {pricedate} {queryType} 总高度 {height}次,视图固定高度{viewHeight}")

                if height == last_height:
                    same_count += 1
                    if same_count >= scroll_end_max_count:
                        # logging.info(f"Tab {tab_index}  {city} {pricedate} {queryType} 页面已滚动{scroll_count}次到底，有效滚动 {effecttive_scroll_count}次")
                        break
                else:
                    # effecttive_scroll_count = effecttive_scroll_count + 1
                    # logging.info(f"Tab {tab_index}  {city} {pricedate} {queryType} 有效滚动 {effecttive_scroll_count}次")
                    same_count = 0
                    last_height = height

            # 获取酒店数据
            hotels = self.page.s_eles('@class=hotel-card-list-resize ng-star-inserted')

            # logging.info(f"城市 {city} 的 {queryType} 数据，共找到 {len(hotels)} 个酒店")
            hotel_list = []
            for hotel in hotels:
                hotel_data = {
                    'city': {city},
                    'name': hotel.ele('@data-slnm-ihg=brandHotelNameSID').text if hotel.ele('@data-slnm-ihg=brandHotelNameSID') else '',
                    'minvalue': -1,
                    'mintype': 0 #默认0，表示既不是最低房价，页不是最低所需积分。1:房价；2：积分
                }
                if queryType == 'price':
                    price_div = hotel.ele('@data-slnm-ihg=hotelPirceSID')
                    hotel_data['mintype'] = 1
                    if price_div:
                        price_text = price_div.text.strip()
                        currency = price_div.ele('tag:span')
                        if currency:
                            price = price_text.replace(currency.text, '').strip()
                            hotel_data['minvalue'] = int(price.replace(',', ''))
                elif queryType == 'points':
                    points_div = hotel.ele('@data-slnm-ihg=dailyPointsCostSID')
                    hotel_data['mintype'] = 2
                    if points_div:
                        points = points_div.text.strip()
                        hotel_data['minvalue'] = int(points.replace(',', ''))
                hotel_list.append(hotel_data)
            # logging.info(f"===酒店列表：{hotel_list}===")
            return hotel_list

        except Exception as e:
            logging.error(f"加载 {city} {pricedate} {queryType} 的数据时发生错误：{e}")
            logging.error("Stack trace:\n%s", traceback.format_exc())  # 使用 traceback.format_exc() 获取堆栈信息

            return []

    def close_browser(self):
        """
        关闭浏览器
        """
        self.page.quit()
        logging.info("浏览器已关闭")
        
def process_city(loader, city, result_queue):
    version = datetime.now().strftime('%Y-%m-%d %H:%M')
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
        
        # 价格和积分数据
        price_result = []
        points_result = []
        
        loader4Load = LoadPriceHIG()
        price_start_time = time.time()
        price_result = loader.loadData(city, pricedate, priceURL, 'price')
        save(loader4Load, version, pricedate, price_result)
        price_end_time = time.time()
        logging.info(f"***price 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的记录数：{len(price_result)}，耗时：{price_end_time - price_start_time:.2f} 秒)")
        
        points_start_time = time.time()
        points_result = loader.loadData(city, pricedate, pointsURL, 'points')
        save(loader4Load, version, pricedate, points_result)
        points_end_time =  time.time()
        logging.info(f"***points 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的记录数：{len(points_result)}，耗时：{points_end_time - points_start_time:.2f} 秒)")

        # 更新日期
        pricedate += timedelta(days=1)
        
    days_end_time = time.time()
    logging.info(f"==={city} {MAX_DAYS_COUNT} 天 总耗时：{days_end_time - days_start_time:.2f} 秒)")
    result_queue.put(f"城市 {city} {MAX_DAYS_COUNT} 天数据爬取完成")
    
    logging.info(f"==={city} {MAX_DAYS_COUNT} 天 {version} 版本 开始去重)")   
    #去重。同一批次、同一酒店、同一数据类型、同一天的数据，保留1个
    loader.db.remove_duplicates('hotelprice', ['version', 'name', 'mintype', 'pricedate'], conditions=f"t1.city = '{city}' AND t1.version = '{version}'")
    logging.info(f"==={city} {MAX_DAYS_COUNT} 天 {version} 版本 去重成功")   
    #保存1个城市的1个酒店的1天价格信息，到DB
def save(loader, version, pricedate, hotel_list):
    #转一下

    # 保存到数据库
    for hotel in hotel_list:
        hotel['version'] = version
        hotel['pricedate'] = pricedate
        loader.db.insert_data('hotelprice', hotel)

def main(args):
    result_queue = Queue()
    loader = LoadPriceHIG()
    
    # # 从 city 表中查询所有城市名称
    # query_result = loader.db.query_data(
    #     'city', 
    #    conditions="hotelavailable != 0 AND level IN (0, 1) ORDER BY level ASC")
    # cities = [row['name'] for row in query_result]  # 提取 name 列的值
    # logging.info(f"从DB得到城市列表：{cities}")

    #测试用城市列表
    # cities = CITIES
    cities = args

    try:
        """"
        频率：至少1-5h跑一遍
        注：默认的page会打开一个tab，加上这里指定打开的固定tab数。总tab数比定义的多1个。
        操作定义的tab时，还是从0开始（0不会操作到page默认tab）
        速度:
            本地：1城的所有数据(价格+积分)：18-30s，中位数19-22.2s
            服务器：13s
        统计：
        03.26
        city day type totaltime(s) average  总记录 条数据/分钟
        本地：
        3 2 2 154 12    5
        8 2 2 347 10.8  6
        1 3 2 48  x     251    313    365天，1城，预计1.6小时。
        1 120 2 1393  x     9268    400    4个月数据，23分钟。365天，1城，预计70分钟。
        11 30 2 20分钟 xx  349 17    17:52执行到18:12共20分钟（一分钟17条数据，速度还可以），后来一直到17:00都在报错，且无数据产生
        1 365 2 59分钟  x     4685    79    12个月数据，59分钟。数据明显少了，一天才12条。
        1 365 2 118分钟  x    29951    254    12个月数据，118分钟。
        服务器：
        1 365 2 130分钟  x    27605    254    北京12个月数据，130分钟。服务器
        
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

        cities_start_time = time.time()

        for city in cities:
            process_city(loader, city, result_queue)

        cities_end_time = time.time()
        logging.info(f"###{len(cities)} 个城市， {MAX_DAYS_COUNT} 天 总耗时：{cities_end_time - cities_start_time:.2f} 秒)")

        # 打印结果
        while not result_queue.empty():
            logging.info(result_queue.get())

    finally:
        # 关闭浏览器
        loader.close_browser()


if __name__ == '__main__':
    # 本地模拟设置 sys.argv
    # sys.argv = ['main.py', '北京']
    
    # 这里 args 是从 crontab 传递过来的参数。只取数组的第一个元素城市
    logging.info(f"===查{sys.argv}洲际，{MAX_DAYS_COUNT}天的价格，edge===")
    # 获取 crontab 传递的参数
    args = sys.argv[1:]
    main(args)