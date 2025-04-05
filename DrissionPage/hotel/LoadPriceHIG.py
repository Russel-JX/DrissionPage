from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions
from datetime import timedelta
import time
import traceback
from util.HotelDatabase import HotelDatabase
import logging


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
        # co.headless()
        # # 修改 User-Agent.可以解决无头模式的反扒问题！
        # co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

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

    #TODO 切换tab页面的方法要搞
    """
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



    """
    TODO 同时打开多个tab时，有时有的tab不被点击选中，tab内容不会渲染，导致程序一直等待。
    方案：可在其他tab执行完成后，去点击卡住的tab，让程序继续。
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
            for _ in range(15):  # 最多滚动 15 次
                """
                TODO
                激活所有 tab，确保每个 tab 都能顺利加载内容，这样做有问题。3个城市跑了6分钟。（单线程才3分钟）
                时间都消耗在了tab切换上了。因为每个线程这个位置，都去切换所有线程，不管当前线程是否正在有效处理数据。
                注释掉_activate_all_tabs中的time.sleep(1)后，快了。1分51秒(切换耗时46秒，占比41.4%)
                下一步：
                    找到更合理的切换时机，或者
                    新开线程来控制这些子线程的运行
                    _activate_all_tabs中，当前等待跑的线程数<tab数时，只切换那些再跑的tab。完全结束的tab不用切换。
                """
                # self._activate_all_tabs() #无头模式下，无需获取页面焦点。因为脚本会自动操作页面。

                tab.scroll.to_bottom()
                # time.sleep(1)
                height = tab.run_js('document.body.scrollHeight')

                if height == last_height:
                    same_count += 1
                    if same_count >= 3:
                        # logging.info(f"Tab {tab_index}  {city} {pricedate} {queryType} 页面已滚动到底")
                        break
                else:
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