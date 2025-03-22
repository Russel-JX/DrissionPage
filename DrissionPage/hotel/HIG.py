from DrissionPage import ChromiumPage
from pathlib import Path
import time

# 当前文件路径
file_path = Path(__file__)
start_time = time.time()
page = ChromiumPage()
print(f'===={file_path.name}执行开始！====')
page.get('https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false')  # 示例页面

# 下滑到底，获取更多内容
last_height = 0
same_count = 0

for i in range(30):  # 最多下滑30次
    page.scroll.to_bottom()
    time.sleep(2)  # 等待加载

    height = page.run_js('document.body.scrollHeight')
    # print(f'页面高度：{height}')

    if height == last_height:
        same_count += 1
        if same_count >= 3:
            print("滑到底了，停止滚动。")
            break
    else:
        same_count = 0
        last_height = height

hotels = page.eles('@class=hotel-card-list-resize ng-star-inserted')
print("======酒店总数======",len(hotels))
i# 遍历所有price的<div>元素
for hotel in hotels:
    name = hotel.ele('@data-slnm-ihg=brandHotelNameSID')
    price = hotel.ele('@class=price')
    #有的酒店名只在属性为data-slnm-ihg=hotelNameSID下
    #如<div _ngcontent-ng-c278914146="" class="title hotel-name ng-star-inserted" data-slnm-ihg="hotelNameSID"><span _ngcontent-ng-c278914146="" id="hotel-card-title-PEKCH">北京丽都维景酒店</span></div>
     #TODO 这里执行很慢，要优化
    if not name:
        name = hotel.ele('@data-slnm-ihg=hotelNameSID').ele('tag:span')
    #有的酒店所查日期内，没有可用房源和价格时，价格在class=availability-message mb-4
    #如<div _ngcontent-ng-c2686815634="" class="availability-message mb-4" data-testid="noRoomsAvail">所选日期无空房</div>
    #TODO 这里执行很慢，要优化
    if not price:
        price = hotel.ele('@class=availability-message mb-4')
    # 打印酒店名、价格信息
    # print(f'酒店名称：{name.text}, 价格{price.text}')
end_time = time.time()
#耗时67.39秒
print(f'===={file_path.name}执行成功完成！耗时{end_time - start_time:.2f}秒====')
page.quit()
