from datetime import datetime

from sqlalchemy import Column, types
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import ForeignKey

from util.orm import AlchemyMixin, Base
from .city import City, District, BizCircle
from .community import Community

'''
{
			"house_code": "101101986670",
			"title": "后芳嘉园胡同 1室1厅 680万",
			"desc": "1室1厅\/55.56㎡\/南\/后芳嘉园胡同",
			"price_str": "680",
			"price_unit": "万",
			"unit_price_str": "122,391元\/平",
			"cover_pic": "http:\/\/image1.ljcdn.com\/110000-inspection\/72a65e25-a4b2-48e1-8e2d-f9b0af0bf7d1.jpg.280x210.jpg",
			"color_tags": [{
				"desc": "满五年",
				"color": "ff8062"
			}, {
				"desc": "房主自荐",
				"color": "f2a12f"
			}, {
				"desc": "地铁",
				"color": "59abfd"
			}],
			"is_vr": false,
			"is_video": false,
			"card_type": "house",
			"is_focus": false,
			"basic_list": [{
				"name": "售价",
				"value": "680万"
			}, {
				"name": "房型",
				"value": "1室1厅"
			}, {
				"name": "建筑面积",
				"value": "55.56㎡"
			}],
			"info_list": [{
				"name": "单价：",
				"value": "122391元\/平"
			}, {
				"name": "挂牌：",
				"value": "2017.08.23"
			}, {
				"name": "朝向：",
				"value": "南"
			}, {
				"name": "楼层：",
				"value": "顶层\/6层"
			}, {
				"name": "楼型：",
				"value": "板楼"
			}, {
				"name": "电梯：",
				"value": "无"
			}, {
				"name": "装修：",
				"value": "精装"
			}, {
				"name": "年代：",
				"value": "2003年"
			}, {
				"name": "用途：",
				"value": "普通住宅"
			}, {
				"name": "权属：",
				"value": "二类经济适用房"
			}],
			"community_name": "后芳嘉园胡同",
			"baidu_la": 39.926105,
			"baidu_lo": 116.436201,
			"blueprint_hall_num": 1,
			"blueprint_bedroom_num": 1,
			"area": 55.56,
			"price": 6800000,
			"unit_price": 122391
		},
'''


class House(AlchemyMixin, Base):
    __tablename__ = 'houses'

    id = Column(types.BigInteger, primary_key=True)
    city_id = Column(types.Integer, ForeignKey(City.id), nullable=False)
    district_id = Column(types.Integer, ForeignKey(District.id), nullable=False)
    biz_circle_id = Column(types.Integer, ForeignKey(BizCircle.id), nullable=False)
    commonity_id = Column(types.BigInteger, ForeignKey(Community.id), nullable=False)
    commonity_name = Column(types.String(64))
    title = Column(types.String(64), nullable=False)
    desc = Column(types.String(64))  # 简介
    cover_pic = Column(types.String(128))  # 封面
    color_tags = Column(types.JSON)  # 高亮标签
    basic_list = Column(types.JSON)  # 基本信息
    info_list = Column(types.JSON)  # 详细信息
    baidu_la = Column(types.Float)  # 百度纬度
    baidu_lo = Column(types.Float)  # 百度经度
    blueprint_hall_num = Column(types.Integer)  # 厅数
    blueprint_bedroom_num = Column(types.Integer)  # 卧室数
    area = Column(types.Float)  # 面积
    price = Column(types.Float)  # 总价
    unit_price = Column(types.Float)  # 单价
    updated_at = Column(types.DateTime, nullable=False, default=datetime.now)
    page_fetched_at = Column(types.DateTime)

    def __init__(self, city_id, district_id, biz_circle_id, community_id, info):
        self.id = int(info['house_code'])
        self.city_id = city_id
        self.district_id = district_id
        self.biz_circle_id = biz_circle_id
        self.commonity_id = community_id
        self.commonity_name = info['community_name']
        self.title = info['title']
        self.desc = info['desc']
        self.cover_pic = info['cover_pic']
        self.color_tags = info['color_tags'] if 'color_tags' in info else None
        self.basic_list = info['basic_list']
        self.info_list = info['info_list']
        self.baidu_la = float(info['baidu_la'])
        self.baidu_lo = float(info['baidu_lo'])
        self.blueprint_hall_num = int(info['blueprint_hall_num'])
        self.blueprint_bedroom_num = int(info['blueprint_bedroom_num'])
        self.area = float(info['area'])
        self.price = float(info['price'])
        self.unit_price = float(info['unit_price'])
