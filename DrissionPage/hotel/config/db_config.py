import os

# 数据库连接配置
DB_CONFIGS = {
    'development': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'database': 'hotel',
        'charset': 'utf8',
        'connect_timeout': 20  # 设置超时时间为 20 秒
    },
    'testing': {
        'host': '114.132.237.123',
        'port': 3306,
        'user': 'root',
        'password': 'root!@2024',
        'database': 'hotel',
        'charset': 'utf8',
        'connect_timeout': 20  # 设置超时时间为 20 秒
    },
    'production': {
        'host': '114.132.237.123',
        'port': 3306,
        'user': 'root',
        'password': 'root!@2024',
        'database': 'hotel',
        'charset': 'utf8',
        'connect_timeout': 20  # 设置超时时间为 20 秒
    }
}

# 获取当前环境，默认为 development
# CURRENT_ENV = os.getenv('DB_ENV', 'development')
CURRENT_ENV = 'development'
# CURRENT_ENV = 'production'



# 根据当前环境选择配置
DB_CONFIG = DB_CONFIGS[CURRENT_ENV]