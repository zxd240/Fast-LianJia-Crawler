import logging
import os
import sys
from datetime import datetime, timedelta

import requests

import monkey
import util
from config import config
from lian_jia import City, District, BizCircle, Community, House
from util.orm import Session

# 行政区名称 id 映射, 如: 海淀 -> 23008618
DISTRICT_MAP = {}


def get_house():
    db_session = Session()
    communities = db_session.query(Community).filter(
        Community.second_hand_quantity != 0
    ).all()
    for community in communities:
        get_house_by_community(community)


def main():
    city_id = config.city_id
    #get_house()
    update_city(city_id)
    update_communities(city_id)


def update_city(city_id):
    """
    初始化/更新城市信息
    """
    logging.info('初始化/更新城市信息... city_id={}'.format(city_id))

    city_info = get_city_info(city_id)
    city = City(city_info)

    db_session = Session()
    db_session.merge(city)
    for district_info in city_info['district']:
        district = District(city.id, district_info)
        logging.info('城市={}, 区域={}, 商圈数={}'.format(city.name, district.name, district.biz_circles_count))
        DISTRICT_MAP[district.name] = district.id
        db_session.merge(district)

        for biz_circle_info in district_info['bizcircle']:
            biz_circle = db_session.query(BizCircle).filter(
                BizCircle.id == int(biz_circle_info['bizcircle_id'])
            ).first()
            if biz_circle:
                # 记录已存在，可能需要更新 district_id
                #
                if district.id not in biz_circle.district_id:
                    # biz_circle.district_id.append()、district_id += 等方式都不能更新表
                    dist_list = list(biz_circle.district_id)
                    dist_list.append(district.id)
                    biz_circle.district_id = tuple(dist_list)
            else:
                biz_circle = BizCircle(city.id, district.id, biz_circle_info)
                db_session.add(biz_circle)

    db_session.commit()
    db_session.close()

    logging.info('初始化/更新城市信息结束.')


def get_city_info(city_id):
    """
    获取城市信息
    """
    url = 'http://app.api.lianjia.com/config/config/initData'

    payload = {
        'params': '{{"city_id": {}, "mobile_type": "android", "version": "8.0.1"}}'.format(city_id),
        'fields': '{"city_info": "", "city_config_all": ""}'
    }

    data = util.get_data(url, payload, method='POST')

    city_info = data['city_info']['info'][0]
    for a_city in data['city_config_all']['list']:
        if a_city['city_id'] == city_id:
            # 查找城市名称缩写
            city_info['city_abbr'] = a_city['abbr']
            break

    else:
        logging.error('# 抱歉, 链家网暂未收录该城市~')
        sys.exit(1)

    return city_info


def update_communities(city_id):
    """
    获取/更新小区信息
    """
    days = 3
    deadline = datetime.now() - timedelta(days=days)
    logging.info('更新久于 {} 天的小区信息...'.format(days))

    db_session = Session()

    biz_circles = db_session.query(BizCircle).filter(
        BizCircle.city_id == city_id,
        (BizCircle.communities_updated_at == None) |
        (BizCircle.communities_updated_at < deadline)
    ).all()

    total_count = len(biz_circles)
    logging.info('需更新总商圈数量: {}'.format(total_count))

    for i, biz_circle in enumerate(biz_circles):
        communities = get_communities_by_biz_circle(city_id, biz_circle.id)
        logging.info('进度={}/{}, 商圈={}, 小区数={}'.format(i + 1, total_count, biz_circle.name, communities['count']))
        update_db(db_session, biz_circle, communities)

    db_session.close()

    logging.info('小区信息更新完毕.')


def get_communities_by_biz_circle(city_id, biz_circle_id):
    """
    按商圈获得小区信息
    """
    url = 'http://app.api.lianjia.com/house/community/search'

    offset = 0

    communities = {
        'count': 0,
        'list': []
    }

    while True:
        params = {
            'bizcircle_id': biz_circle_id,
            'group_type': 'community',
            'limit_offset': offset,
            'city_id': city_id,
            'limit_count': 30
        }

        data = util.get_data(url, params)

        if data:
            communities['count'] = data['total_count']
            communities['list'].extend(data['list'])

            if data['has_more_data']:
                offset += len(data['list'])
            else:
                break
        else:
            # 存在没有数据的时候, 如: http://bj.lianjia.com/xiaoqu/huairouqita1/
            break

    # 去重, 有时链家服务器抽风(或者本身数据就是错误的)... 返回的数据有重复的, 需要处理下
    # 如: http://sh.lianjia.com/xiaoqu/hengshanlu/
    d = {community['community_id']: community for community in communities['list']}
    communities['list'] = d.values()

    return communities


def update_db(db_session, biz_circle, communities):
    """
    更新小区信息, 商圈信息
    """
    db_session.query(Community).filter(
        Community.biz_circle_id == biz_circle.id
    ).delete()
    community_objs = []
    for community_info in communities['list']:
        try:
            district_id = DISTRICT_MAP[community_info['district_name']]
            community = Community(biz_circle.city_id, district_id, biz_circle.id, community_info)
            db_session.add(community)
            community_objs.append(community)
        except Exception as e:
            # 返回的信息可能是错误的/不完整的, 如小区信息失效后返回的是不完整的信息
            # 如: http://sz.lianjia.com/xiaoqu/2414168277659446
            logging.error('错误: 小区 id: {}; 错误信息: {}'.format(community_info['community_id'], repr(e)))

    biz_circle.communities_count = communities['count']
    biz_circle.communities_updated_at = datetime.now()

    db_session.commit()

    # 得到小区的房源信息
    for community in community_objs:
        get_house_by_community(community)


def proxy_patch():
    """
    Requests 似乎不能使用系统的证书系统, 方便起见, 不验证 HTTPS 证书, 便于使用代理工具进行网络调试...
    http://docs.python-requests.org/en/master/user/advanced/#ca-certificates
    """
    import warnings
    from requests.packages.urllib3.exceptions import InsecureRequestWarning

    class XSession(requests.Session):
        def __init__(self):
            super().__init__()
            self.verify = False

    requests.Session = XSession
    warnings.simplefilter('ignore', InsecureRequestWarning)


def get_house_by_community(community):
    """
    按小区获得房子信息
    """
    url = 'http://app.api.lianjia.com/house/ershoufang/searchv4'
    offset = 0

    houses = {
        'count': 0,
        'list': []
    }

    while True:
        params = {
            "comunityIdRequest": "c" + str(community.id),
            "city_id": community.city_id,
            "limit_offset": offset,
            "condition": "c" + str(community.id),
            "queryStringText": community.name,
            "limit_count": 20,
        }
        print(params)
        data = util.get_data(url, params)
        if data['total_count'] == 0:
            # 没有数据, 小区房源数不准确
            break

        if data:
            houses['count'] = data['total_count']
            house_count = 0
            if 'list' not in data:
                logging.warn("get houses list failed: %s"%data)
                break
            for house in data['list']:
                ### 还有一些不是房子的数据
                if 'house_code' in house:
                    house_count += 1
                    houses['list'].append(house)

            if data['has_more_data']:
                offset += house_count
            else:
                break
        else:
            # 存在没有数据的时候, 如: http://bj.lianjia.com/xiaoqu/huairouqita1/
            break

    # 去重, 有时链家服务器抽风(或者本身数据就是错误的)... 返回的数据有重复的, 需要处理下
    # 如: http://sh.lianjia.com/xiaoqu/hengshanlu/
    d = {house['house_code']: house for house in houses['list']}
    houses['list'] = d.values()
    update_houses_db(community, houses)


def update_houses_db(community, houses):
    """
    更新小区信息, 商圈信息
    """
    db_session = Session()
    db_session.query(House).filter(
        House.commonity_id == community.id
    ).delete()

    for house_info in houses['list']:
        try:
            house = House(community.city_id, community.district_id, community.biz_circle_id, community.id, house_info)
            db_session.add(house)
        except Exception as e:
            # 返回的信息可能是错误的/不完整的, 如小区信息失效后返回的是不完整的信息
            # 如: http://sz.lianjia.com/xiaoqu/2414168277659446
            logging.error('错误: 二手房 id: {}; 错误信息: {}'.format(house_info['house_code'], repr(e)))

    db_session.commit()
    db_session.close()
    return houses


if __name__ == '__main__':
    if config.debug and os.getenv('HTTPS_PROXY'):
        proxy_patch()

    monkey.do_patch()
    main()
