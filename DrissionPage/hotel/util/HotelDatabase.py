# 数据库操作类
import pymysql
from config.db_config import DB_CONFIG
import logging
import traceback

class HotelDatabase:
    def __init__(self):
        self.connection = pymysql.connect(**DB_CONFIG)
        self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)

    def insert_data(self, table, data):
        """
        插入数据到指定表
        :param table: 表名
        :param data: 字典形式的数据
        """
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({keys}) VALUES ({values})"
        try:
            self.cursor.execute(sql, tuple(data.values()))
            self.connection.commit()
            # logging.info(f"数据插入成功：{data}")
        except Exception as e:
            self.connection.rollback()
            logging.info(f"插入数据失败：{e}")
            logging.error("Stack trace:\n%s", traceback.format_exc())

    def query_data(self, table, conditions=None):
        """
        查询数据
        :param table: 表名
        :param conditions: 查询条件（字典形式）
        :return: 查询结果列表
        """
        sql = f"SELECT * FROM {table}"
        params = []
        if isinstance(conditions, dict):  # 如果条件是字典
            condition_str = ' AND '.join([f"{k}=%s" for k in conditions.keys()])
            sql += f" WHERE {condition_str}"
            params = list(conditions.values())
        elif isinstance(conditions, str):  # 如果条件是字符串
            sql += f" WHERE {conditions}"
        try:
            self.cursor.execute(sql, params)
            results = self.cursor.fetchall()
            logging.info(f"查询{sql}结果总数：{len(results)}")
            return results
        except Exception as e:
            logging.error(f"查询数据失败：{e}")
            logging.error("Stack trace:\n%s", traceback.format_exc())
            return []

    def close(self):
        """关闭数据库连接"""
        self.cursor.close()
        self.connection.close()