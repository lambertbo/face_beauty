#coding: utf-8
import time
import os
import re
import requests
from lxml import etree
from aip import AipFace
import urllib
import base64
import chardet

APP_ID = '15528557'
API_KEY = '0lWqcU5h1MrGzvbnUYXp1vSF'
SECRET_KEY = 'UYknUWhFGqk8YvCzbhD1Wv9e8gza2zuX '

Authorization = 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20'

filePath = 'image'

Limit = 5
SOURCE = '19552207'
#爬虫假装下正常浏览器请求
USER_AGENT = "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/534.55.3 (KHTML, like Gecko) Version/5.1.5 Safari/534.55.3"
#爬虫假装下正常浏览器请求
REFERER = "https://www.zhihu.com/topic/%s/newest" % SOURCE
#某话题下讨论列表请求 url
BASE_URL = "https://www.zhihu.com/api/v4/topics/%s/feeds/timeline_activity"
#初始请求 url 附带的请求参数
URL_QUERY = "?include=data%5B%3F%28target.type%3Dtopic_sticky_module%29%5D.target.data%5B%3F%28target.type%3Danswer%29%5D.target.content%2Crelationship.is_authorized%2Cis_author%2Cvoting%2Cis_thanked%2Cis_nothelp%3Bdata%5B%3F%28target.type%3Dtopic_sticky_module%29%5D.target.data%5B%3F%28target.type%3Danswer%29%5D.target.is_normal%2Ccomment_count%2Cvoteup_count%2Ccontent%2Crelevant_info%2Cexcerpt.author.badge%5B%3F%28type%3Dbest_answerer%29%5D.topics%3Bdata%5B%3F%28target.type%3Dtopic_sticky_module%29%5D.target.data%5B%3F%28target.type%3Darticle%29%5D.target.content%2Cvoteup_count%2Ccomment_count%2Cvoting%2Cauthor.badge%5B%3F%28type%3Dbest_answerer%29%5D.topics%3Bdata%5B%3F%28target.type%3Dtopic_sticky_module%29%5D.target.data%5B%3F%28target.type%3Dpeople%29%5D.target.answer_count%2Carticles_count%2Cgender%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics%3Bdata%5B%3F%28target.type%3Danswer%29%5D.target.content%2Crelationship.is_authorized%2Cis_author%2Cvoting%2Cis_thanked%2Cis_nothelp%3Bdata%5B%3F%28target.type%3Danswer%29%5D.target.author.badge%5B%3F%28type%3Dbest_answerer%29%5D.topics%3Bdata%5B%3F%28target.type%3Darticle%29%5D.target.content%2Cauthor.badge%5B%3F%28type%3Dbest_answerer%29%5D.topics%3Bdata%5B%3F%28target.type%3Dquestion%29%5D.target.comment_count&limit=" + str(Limit)

#指定 url，获取对应原始内容 / 图片
def fetch_image(url):
    try:
        headers = {
                "User-Agent": USER_AGENT,
                "Referer": REFERER,
                "authorization": Authorization
                }
        s = requests.get(url, headers=headers)
    except Exception as e:
        print("fetch last activities fail. " + url)
        raise e

    return s.content
def init_face_detective(app_id, api_key, secret_key):
    client = AipFace(app_id, api_key, secret_key)
    #人脸检测中，在响应中附带额外的字段。年龄 / 性别 / 颜值 / 质量
    #options = {"face_fields": "age,beauty,gender,qualities"} 
    #print(options)
    imageType = "BASE64"
    
    options = {}
    options["face_field"] = "age,beauty,gender,qualities"

    def detective(image):
        r = client.detect(image,imageType,options)
        #如果没有检测到人脸
        print(r)
        if r["result"]["face_num"] == 0:
            return []
        scores = []
        for face in r["result"]["face_list"]:
            #人脸置信度太低
            if face["face_probability"] < 0.6:
                continue
            #真实人脸置信度太低
            if face["qualities"]["type"]["human"] < 0.6:
                continue
            #颜值低于阈值
            if face["beauty"] < 45:
                continue
            #性别非女性
            if face["gender"] != "female":
                continue
            scores.append(face["beauty"])
        return scores
    return detective

def fetch_activities(url):
    try:
        headers = {
                "User-Agent": USER_AGENT,
                "Referer": REFERER,
                "authorization": Authorization
                }
        s = requests.get(url, headers=headers,verify = False)
    except Exception as e:
        print("fetch last activities fail. " + url)
        raise e
    return s.json()

face_detective = init_face_detective(APP_ID, API_KEY, SECRET_KEY)
url = BASE_URL % SOURCE + URL_QUERY
datums = fetch_activities(url)

for data in datums["data"]:
    target = data["target"]
    if "content" not in target or "question" not in target or "author" not in target:
        continue
    #解析列表中每一个元素的内容
    html = etree.HTML(target["content"])
    seq = 0
    #question_url = target["question"]["url"]
    question_title = target["question"]["title"]
    author_name = target["author"]["name"]
    #author_id = target["author"]["url_token"]
    print("current answer: " + question_title + " author: " + author_name)
    #获取所有图片地址
    images = html.xpath("//img/@src")
    for image in images:
        if not image.startswith("http"):
            continue
        s = fetch_image(image)    
        s = base64.b64encode(s)
        s = s.decode()
        print(s)
        #请求人脸检测服务
        scores = face_detective(s)
        for score in scores:
            filename = ("%d--" % score) + author_name + "--" + question_title + ("--%d" % seq) + ".jpg"
            filename = re.sub(r'(?u)[^-\w.]', '_', filename)
            #注意文件名的处理，不同平台的非法字符不一样，这里只做了简单处理，特别是 author_name / question_title 中的内容
            seq = seq + 1
            with open(os.path.join(filePath, filename), "wb") as fd:
                fd.write(s)
        #人脸检测 免费，但有 QPS 限制
        time.sleep(2)