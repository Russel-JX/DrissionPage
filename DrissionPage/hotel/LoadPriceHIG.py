from DrissionPage import ChromiumPage
from datetime import datetime, timedelta
import time
import traceback
from util.HotelDatabase import HotelDatabase
from util.StrUtil import StrUtil


class LoadPriceHIG:
    def __init__(self):
        self.db = HotelDatabase()
        self.page = ChromiumPage()  # 创建一个全局的浏览器实例
        self.tabs = {}  # 存储每个城市对应的 tab

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
    
    def open_tabs_for_cities(self, cities):
        """
        为每个城市打开一个新的 tab 页面
        关于tab操作的文档：
        https://github.com/Russel-JX/DrissionPage/blob/master/docs_en/ChromiumPage/tab_operation.md
        """
        for city in cities:
            #新建tab。TODO这里新建tab时，可以直接给url去请求，快
            self.tabs[city] = self.page.new_tab()
            print(f"为城市 {city} 打开了新的 tab 页面{self.tabs[city]}")
        print(f'====现有总tab数：{self.page.tabs_count}')  
    def switch_to_all_tabs(self):
        """
        切换到每个 tab 页面一次，确保页面聚焦并充分渲染
        """
        for city, tab in self.tabs.items():
            print(f"====为城市 {city} 切换了的 tab 页面{tab}")
            """
            有简单方式切换tab。
            老的都不好用：
                self.page.set_active_tab(index=0)
                self.page.driver.switch_to_window(driver.current_window_handle)
            """
            tab.set.activate()
            print(f"切换到城市 {city} 的 tab 页面")
            time.sleep(1)  # 等待页面渲染完成

    def loadData(self, url, city, queryType, pricedate):
        """
        加载单个城市的价格或积分数据
        """
        try:
            self.tabs[city].set.activate()  # 切换到对应城市的 tab
            self.page.get(url)  # 打开目标页面

            # 滚动页面，确保内容加载完全
            last_height = 0
            same_count = 0
            for _ in range(15):  # 最多滚动 15 次
                self.page.scroll.to_bottom()
                time.sleep(1)
                height = self.page.run_js('document.body.scrollHeight')
                if height == last_height:
                    same_count += 1
                    if same_count >= 3:
                        print(f"{city} 的 {queryType} 页面已滚动到底")
                        break
                else:
                    same_count = 0
                    last_height = height

            # 获取酒店数据
            hotels = self.page.s_eles('@class=hotel-card-list-resize ng-star-inserted')
            print(f"城市 {city} 的 {queryType} 数据，共找到 {len(hotels)} 个酒店")
            hotel_list = []
            for hotel in hotels:
                hotel_data = {
                    'name': hotel.ele('@data-slnm-ihg=brandHotelNameSID').text if hotel.ele('@data-slnm-ihg=brandHotelNameSID') else '',
                    'price': -1,
                    'points': -1
                }
                if queryType == 'price':
                    price_div = hotel.ele('@data-slnm-ihg=hotelPirceSID')
                    if price_div:
                        price_text = price_div.text.strip()
                        currency = price_div.ele('tag:span')
                        if currency:
                            price = price_text.replace(currency.text, '').strip()
                            hotel_data['price'] = int(price.replace(',', ''))
                elif queryType == 'points':
                    points_div = hotel.ele('@data-slnm-ihg=dailyPointsCostSID')
                    if points_div:
                        points = points_div.text.strip()
                        hotel_data['points'] = int(points.replace(',', ''))
                hotel_list.append(hotel_data)
            return hotel_list

        except Exception as e:
            print(f"加载城市 {city} 的 {queryType} 数据时发生错误：{e}")
            traceback.print_exc()
            return []

    def close_browser(self):
        """
        关闭浏览器
        """
        self.page.quit()
        print("浏览器已关闭")