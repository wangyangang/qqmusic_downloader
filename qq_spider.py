import requests
from urllib.parse import urlencode
import json
import re
import os
import math
import csv


class Spider:
    def __init__(self, play_lists):
        self.play_lists = play_lists

    def run(self):
        # 这个接口可以根据歌单id获取里面包含的所有歌曲的信息。包括歌名，歌手，专辑，时长和歌曲的标识符song_mid等信息
        base_url = 'https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg'
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'dnt': '1',
            'origin': 'https://y.qq.com',
            'pragma': 'no-cache',
            'referer': 'https://y.qq.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36'
        }
        # params是需要传递的数据，其中disstid是歌单的id
        params = {
            'type': '1',
            'json': '1',
            'utf8': '1',
            'onlysong': '0',
            'new_format': '1',
            'disstid': '',
            'g_tk_new_20200303': '5381',
            'g_tk': '5381',
            'loginUin': '0',
            'hostUin': '0',
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'notice': '0',
            'platform': 'yqq.json',
            'needNewCode': '0'
        }
        # logs记录歌单里的歌曲信息，和下载状态，成功或是失败
        logs = list()

        # 遍历歌单id列表，每个歌单id请求一次接口，获取歌单的信息
        for play_list in self.play_lists:
            params.update(disstid=play_list)
            url = base_url + '?' + urlencode(params)

            # 通过requests获取数据，返回值是json字符串
            ret = requests.get(url=url, headers=headers)
            ret = ret.json()
            # 获取歌曲列表
            songlist = ret.get('cdlist')[0].get('songlist')

            # 遍历歌曲列表，依次下载歌曲
            for index, song in enumerate(songlist):
                title = song['title']  # 歌名
                mid = song['mid']      # 歌曲mid
                singer = song['singer'][0].get('title')  # 歌手
                album = song['album'].get('title')       # 专辑名
                interval = song['interval']              # 歌曲时长，单位：秒
                interval_minutes = math.floor(int(interval) / 60)  # 计算分钟数
                interval_seconds = int(interval) % 60              # 除了分钟数以外的秒数
                # 构造时长字符串：格式为 05:04
                interval = str(interval_minutes).rjust(2, '0') + ':' + str(interval_seconds).rjust(2, '0')
                # 调用download方法，下载歌曲，返回下载结果。返回值为数字，1表示成功，-1表示失败
                download_status = self.download(play_list, mid, title)
                download_status = '成功' if download_status == 1 else '失败'
                # 给logs列表添加一个值，内容为歌曲的基本信息和下载状态的字典
                logs.append({
                    'title': title,
                    'singer': singer,
                    'album': album,
                    'interval': interval,
                    'download_status': download_status
                })
                msg = 'playlist %s %s of %s %s %s' % \
                      (play_list, str(index+1), str(len(songlist)), title, download_status)
                print(msg)
                break

        # 保存下载记录到csv文件。
        with open('下载记录.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['歌曲', '歌手', '专辑', '时长', '下载状态'])
            for line in logs:
                row = [line['title'], line['singer'], line['album'], line['interval'], line['download_status']]
                writer.writerow(row)

    @staticmethod
    def download(play_list, song_mid, music_name):
        """
        下载歌曲的方法
        :param play_list: 歌单id
        :param song_mid: 歌曲的mid
        :param music_name: 歌曲的名称
        :return: 下载状态。1表示成功；-1表示失败
        """
        download_status = -1
        # data是url的参数，其中song_mid是歌曲的mid，这个很重要。
        data = json.dumps(
            {
                "req": {
                    "module": "CDN.SrfCdnDispatchServer",
                    "method": "GetCdnDispatch",
                    "param":
                        {
                            "guid": "8809189374",
                            "calltype": 0, "userip": ""
                        }
                },
                "req_0": {
                    "module": "vkey.GetVkeyServer",
                    "method": "CgiGetVkey",
                    "param":
                        {
                            "guid": "8809189374",
                            "songmid": [song_mid],
                            "songtype": [0],
                            "uin": "0",
                            "loginflag": 1,
                            "platform": "20"
                        }
                },
                "comm": {
                    "uin": 0,
                    "format": "json",
                    "ct": 20, "cv": 0
                }
            })
        url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?callback=getplaysongvkey32666490664609316&g_tk=' \
              '5381&jsonpCallback=getplaysongvkey32666490664609316&loginUin=0&hostUin=0&format=jsonp&inCharset=' \
              'utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&data={}'.format(data)

        # 通过请求这个接口，可以获取要下载的歌曲的实际的文件名、vkey、purl等信息。
        # 这些信息是下载音乐文件之前，必须知道的参数。为下载音乐做准备。
        html = requests.get(url)

        # 通过正则表达式，获取到字符串里的json信息。
        music_json = json.loads(re.findall(r'^\w+\((.*)\)$', html.text)[0])

        # filename参数，是类似 C400002hhpfc1IJTuN.m4a 的字符串
        filename = music_json['req_0']['data']['midurlinfo'][0]['filename']

        # vkey参数，是类似 "9EC864C547CFD792A5EBCBB340E570B624466964B7F7EBA376722719CFF752F8E2A30
        # 28BCF058D9E0FE518939EBBBAEA95159D623E6C5563" 的字符串
        vkey = music_json['req_0']['data']['midurlinfo'][0]['vkey']
        download_url = 'http://111.202.85.144/amobile.music.tc.qq.com/{}?guid=8809189374&vkey={}&uin=' \
                       '0&fromtag=66'.format(filename, vkey)

        # purl参数，是类似 "C400002hhpfc1IJTuN.m4a?guid=8809189374&vkey=9EC864C547CFD792A5EBCBB340E570B624466964B7F7
        # EBA376722719CFF752F8E2A3028BCF058D9E0FE518939EBBBAEA95159D623E6C5563&uin=0&fromtag=66" 的字符串
        purl = music_json['req_0']['data']['midurlinfo'][0]['purl']

        # download_url,是真正下载音乐文件的接口
        download_url = 'https://isure.stream.qqmusic.qq.com/' + purl

        # 下载到本地
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/83.0.4103.97 Safari/537.36'
        }
        music = requests.get(download_url, headers=headers)

        # 如果music.ststus_code == 200，表示请求成功。音乐下载成功。
        # 如果等于其它值，表示失败。可能的原因有 没有版权、vip才能听、vvip才能听
        if music.status_code == 200:
            # 去掉歌曲名里的特殊字符，因为特殊字符不能用做下载后的歌曲文件的文件名
            file_name = re.sub(r'[\s+|@<>:\\"/]', '', music_name)
            # 下载到download/歌单id/歌曲1.m4a  这样的路径下
            file_dir = 'download/{}'.format(play_list)
            full_file_name = "{}/{}.m4a".format(file_dir, file_name)
            # 如果 download/歌单id 路径不存在，先要创建一个路径。
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            # 保存音乐文件
            with open(full_file_name, "wb") as m:
                m.write(music.content)
            download_status = 1

        return download_status


if __name__ == "__main__":
    # 歌单列表，比如歌单url是： https://y.qq.com/n/yqq/playlist/7039470358.html#stat=y_new.index.playlist.pic
    # 那么歌单id就是 7039470358
    play_lists = ['7039470358', '2067204233']
    Spider(play_lists).run()
