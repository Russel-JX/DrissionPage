from DrissionPage import ChromiumPage
from pathlib import Path
import time

# 当前文件路径
file_path = Path(__file__)
start_time = time.time()
page = ChromiumPage()
print(f'===={file_path.name}执行开始！====')

# 打开目标页面
page.get('https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false')  # 示例页面

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

# 获取所有酒店卡片
# hotels = page.eles('@class=hotel-card-list-resize ng-star-inserted')
hotels = page.eles('@class=theme-6c')


print("======酒店总数======", len(hotels))

# 遍历酒店卡片，提取信息
for hotel in hotels:
    # 一次性获取所有可能的子元素，减少 DOM 查询次数
    elements = hotel.eles('xpath:*')
    name = None
    price = None

    # 查找酒店名称
    for ele in elements:
        # print(f'***ele:{ele}')
        if ele.attr('data-slnm-ihg') == 'brandHotelNameSID':
            name = ele
            # print(f'***name0：{name}')
            break
    if not name:
        for ele in elements:
            if ele.attr('data-slnm-ihg') == 'hotelNameSID':
                name = ele.ele('tag:span')
                break
    # print(f'***name：{name}')

    # 查找价格信息
    for ele in elements:
        if ele.attr('class') == 'price':
            price = ele
            break
    if not price:
        for ele in elements:
            if ele.attr('data-testid') == 'noRoomsAvail':
                price = ele
                break
    # print(f'***price{price}')

    # 打印酒店名和价格信息
    name_text = name.text if name else '未知酒店'
    price_text = price.text if price else '未知价格'
    print(f'酒店名称：{name_text}, 价格：{price_text}')

end_time = time.time()
print(f'===={file_path.name}执行成功完成！耗时{end_time - start_time:.2f}秒====')
page.quit()