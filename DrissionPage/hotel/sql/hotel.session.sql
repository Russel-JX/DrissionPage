use hotel;
select * from hotel;

#查询重复酒店
select * from hotel where name in ('北京前门富力智选假日酒店') order by id desc;
select count(1), hotelcode, name from hotel group by hotelcode, name having count(hotelcode)>1;

#洲际meta去重
DELETE t1
FROM hotel t1
JOIN hotel t2
ON t1.hotelcode = t2.hotelcode
   AND t1.id > t2.id;
   
#洲际价格积分去重
DELETE t1
FROM hotelprice t1
JOIN hotelprice t2
ON t1.name = t2.name
	AND t1.pricedate =  t2.pricedate
    AND t1.mintype =  t2.mintype
   AND t1.id > t2.id;

   #校验70个主要城市酒店是否拿到
select * from hotel  where  local=1 and  city in( '苏州市') order by id desc;  
select count(1), city from hotel where local=1 and city in('北京市', '天津市', '上海市', '重庆市', '广州市', '深圳市', '成都市', '杭州市', 
'武汉市', '南京市', '苏州市', '西安市', '郑州市', '青岛市', '大连市', '厦门市', 
'沈阳市', '济南市', '合肥市', '长沙市', '福州市', '温州市', '唐山市', '昆明市', 
'长春市', '哈尔滨市', '兰州市', '南昌市', '珠海市', '南宁市', '无锡市', '汕头市', 
'贵阳市', '常州市', '佛山市', '邯郸市', '东莞市', '柳州市', '莆田市', '南通市', 
'洛阳市', '南阳市', '泸州市', '揭阳市', '湛江市', '鞍山市', '宜昌市', '桂林市', 
'株洲市', '唐山市', '临沂市', '大庆市', '宁波市', '邢台市', '茂名市', '赣州市', 
'台州市', '绵阳市', '阜阳市', '安庆市', '洛阳市', '烟台市', '淄博市', '张家口市', 
'海口市', '兰州市', '连云港市', '德州市', '北海市', '四平市', '长治市', '江门市', 
'广安市', '泸州市', '咸阳市', '塔城市', '日照市', '岳阳市', '淮安市', '金华市') group by city order by count(1) desc;
