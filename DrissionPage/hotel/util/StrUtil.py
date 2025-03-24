from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

class StrUtil:
    def replace_URLParam(self, url, params):
        """
        替换 URL 中的 param 参数值
        :param url: 原始 URL
        :param params: 包含多个参数的字典。字典值批量替换字典键对应的参数值
        :return: 替换后的 URL
        """
        # 解析 URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        # 遍历字典，替换或添加参数值
        for key, value in params.items():
            if value:  # 仅替换非空值
                query_params[key] = [value]

        # 重新构造 URL
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse(parsed_url._replace(query=new_query))
        return new_url