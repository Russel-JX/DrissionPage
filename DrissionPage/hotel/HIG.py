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

# 获取所有酒店卡片。使用s_eles代替eles，速度从60s提升至12s
# hotels = page.eles('@class=hotel-card-list-resize ng-star-inserted')
hotels = page.s_eles('@class=hotel-card-list-resize ng-star-inserted')
print("======酒店总数======", len(hotels))

for hotel in hotels:
    # 优先取 brandHotelNameSID，其次 hotelNameSID > span
    name = hotel.ele('@data-slnm-ihg=brandHotelNameSID')
    if not name:
        name_container = hotel.ele('@data-slnm-ihg=hotelNameSID')
        name = name_container.ele('tag:span') if name_container else None

    # 优先取正常价格，其次判断无房价格提示
    price = hotel.ele('@class=price') or hotel.ele('@data-testid=noRoomsAvail')

    # 打印酒店名、价格信息（注意判空）
    print(f"酒店名称：{name.text if name else '未知'}, 价格：{price.text if price else '无'}")

end_time =  time.time()
print(f'===={file_path.name}执行成功完成！耗时 {end_time - start_time:.2f} 秒====')
page.quit()