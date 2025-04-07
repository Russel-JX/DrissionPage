import logging
import os

def setup_logging(log_file='logs/hotel.log', level=logging.INFO):
    """
    配置日志
    :param log_file: 日志文件路径（相对于项目根目录）
    :param level: 日志级别
    """
    # 获取当前文件所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 将 log_file 转换为绝对路径
    log_file_path = os.path.join(base_dir, '..', log_file)

    logging.basicConfig(
        level=level,  # 设置日志级别
        format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
        datefmt='%Y-%m-%d %H:%M:%S',  # 时间格式
        handlers=[
            logging.FileHandler(log_file_path),  # 输出到日志文件
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )