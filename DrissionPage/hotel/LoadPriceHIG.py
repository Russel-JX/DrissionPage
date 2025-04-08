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
        self.tabs = []  # 存储所有 tab 的句柄
        self.db = HotelDatabase()  # 数据库实例

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
                    'minvalue': hotel.get('price', -1),
                    'minpoints': -1  # 初始化积分为-1，表示无房或不能用积分
                }
            else:
                hotel_dict[name]['minvalue'] = hotel.get('price', -1)

        # 遍历积分列表，将积分信息合并到字典中
        for hotel in points_list:
            name = hotel['name']
            if name not in hotel_dict:
                hotel_dict[name] = {
                    'name': name,
                    'minvalue': -1,  # 初始化现金价格为-1，表示无房或不能用现金
                    'minpoints': hotel.get('points', -1),
                    # 'minpoints': hotel.get('points') if isinstance(hotel.get('points'), (int, float)) else -1
                }
            else:
                hotel_dict[name]['minpoints'] = hotel.get('points', -1)

        # 将字典转换为列表。[{},{}]形式
        merged_list = list(hotel_dict.values())
        return merged_list
    
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
    
    def open_tabs(self, count):
        """
        打开指定数量的 tab 页面
        """
        for _ in range(count):
            tab = self.page.new_tab()
            self.tabs.append(tab)
        logging.info(f"====已打开 {len(self.tabs)} 个 tab 页面====")

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
    def loadData(self, city, pricedate, url, queryType, tab_index):
        """
        在指定的 tab 页面中加载数据
        """
        try:
            #当前被使用的tab。tab_index和main.py中的tab_pool.pop(0)对应
            tab = self.tabs[tab_index]
            # logging.info(f"====当前tab： {tab_index} {city} {pricedate} {queryType}====")

            # tab.set.activate()  # 激活指定 tab。无头模式下，无需获取页面焦点。因为脚本会自动操作页面。
            tab.get(url)  # 打开目标页面

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
            for _ in range(25):  # 最多滚动 25 次结束，连续scroll_end_max_count次滚不动也算结束
                # self._activate_all_tabs() #无头模式下，无需获取页面焦点。因为脚本会自动操作页面。

                """
                https://drissionpage.cn/browser_control/ele_operation  元素交互，见元素滚动
                 tab.scroll.to_bottom() 每次一下子滚到tab页底部，页面来不及渲染，导致数据丢失
                 tab.scroll.to_location(300, scroll_height_delta) 每次向下滚动固定距离，保证页面渲染完成
                """
                # tab.scroll.to_bottom()
                # tab.scroll.to_half()
                scroll_height_delta = scroll_height_delta+1500
                tab.scroll.to_location(300, scroll_height_delta)
                # scroll_count = scroll_count+1
                
                # #测试是否能返回值。输出：JavaScript 测试返回值：42   说明js代码可以运行
                # result = tab.run_js('return 42;')  
                # logging.info(f"JavaScript 测试返回值：{result}") 
                
                time.sleep(1)  # 等待 1 秒，确保刚滚下的页面加载完成

                # 每次获取页面总高度，包括当前可见部分和不可见的滚动区域。
                # 注： tab.run_js('return document.body.scrollHeight;') js代码有return才能有返回值，否则拿不到变量值(返回None)！
                # tab.run_js('document.body.scrollHeight;')  # 直接运行js代码，返回None
                height = tab.run_js('return document.body.scrollHeight;') # 总高度= 视图高度+滚动高度。如视图高度2None。13768, 14052
                viewHeight = tab.run_js('return document.documentElement.clientHeight;') # 视图高度。固定840
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
            hotels = tab.s_eles('@class=hotel-card-list-resize ng-star-inserted')

            # logging.info(f"城市 {city} 的 {queryType} 数据，共找到 {len(hotels)} 个酒店")
            hotel_list = []
            for hotel in hotels:
                hotel_data = {
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
            logging.error(f"加载 Tab {tab_index} {city} {pricedate} {queryType} 的数据时发生错误：{e}")
            logging.error("Stack trace:\n%s", traceback.format_exc())  # 使用 traceback.format_exc() 获取堆栈信息

            return []

    def _activate_all_tabs(self):
        """
        依次激活所有 tab，确保每个 tab 都能顺利加载内容
        """
        for i, tab in enumerate(self.tabs):
            try:
                tab.set.activate()
                # logging.info(f"激活 Tab {i}")
                # time.sleep(1)  # 每次激活后等待 1 秒
            except Exception as e:
                logging.warning(f"激活 Tab {i} 时发生错误：{e}")

    def close_browser(self):
        """
        关闭浏览器
        """
        self.page.quit()
        logging.info("浏览器已关闭")
        
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
                    # logging.info(f"***points 城市 {city} 日期 {pricedate.strftime('%Y-%m-%d')} 的记录数：{len(points_result)}，耗时：{end_time - start_time:.2f} 秒)")

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
        3 2 2 154 12    5
        8 2 2 347 10.8  6
        1 3 2 48  x     251    313    365天，1城，预计1.6小时。
        1 120 2 1393  x     9268    400    4个月数据，23分钟。365天，1城，预计70分钟。
        11 30 2 20分钟 xx  349 17    17:52执行到18:12共20分钟（一分钟17条数据，速度还可以），后来一直到17:00都在报错，且无数据产生
        1 365 2 59分钟  x     4685    79    12个月数据，59分钟。数据明显少了，一天才12条。
        1 365 2 118分钟  x    29951    254    12个月数据，118分钟。
        1 365 2 130分钟  x    27605    254    12个月数据，130分钟。服务器
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
    # 模拟设置 sys.argv
    sys.argv = ['main.py', '上海', '苏州']
    # 这里 args 是从 crontab 传递过来的参数。只取数组的第一个元素城市
    logging.info(f"===查{sys.argv}洲际价格，edge===")
    # 获取 crontab 传递的参数
    args = sys.argv[1:]
    main(args)