#本示例演示使用ChromiumPage控制浏览器登录 gitee 网站
from DrissionPage import Chromium, ChromiumOptions

# 配置远程调试端口
options = ChromiumOptions()
options.set_argument('--remote-debugging-port=9222')

# 启动或接管浏览器，并创建标签页对象
tab = Chromium().latest_tab
# 跳转到登录页面
tab.get('https://gitee.com/login')

# 定位到账号文本框，获取文本框元素
ele = tab.ele('#user_login')
# 输入对文本框输入账号
ele.input('您的账号xxx')
# 定位到密码文本框并输入密码
tab.ele('#user_password').input('您的密码xxx')
# 点击登录按钮
tab.ele('@value=登 录').click()