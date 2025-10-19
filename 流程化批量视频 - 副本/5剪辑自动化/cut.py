import os

import json

import uuid

import random

import base64

from glob import glob

from datetime import datetime

\# 最小图片展示时间（秒）

MIN\_IMAGE\_DURATION = 5 # 5秒

def get\_latest\_draft\_folder():

"""

获取最新的剪映草稿文件夹

Returns:

最新草稿文件夹的路径

"""

# 剪映草稿文件夹路径模式（根据实际位置调整）

draft\_pattern = os.path.expanduser("~/Desktop/Youtube/剪映draft/JianyingPro Drafts/\*/draft\_content.json")

# 获取所有草稿文件

draft\_files = glob(draft\_pattern)

if not draft\_files:

raise Exception("未找到剪映草稿文件")

# 按修改时间排序，获取最新的

latest\_draft\_file = max(draft\_files, key=os.path.getmtime)

# 返回包含draft\_content.json的文件夹路径

latest\_draft\_folder = os.path.dirname(latest\_draft\_file)

return latest\_draft\_folder

def microsec\_to\_time(microseconds):

"""将微秒转换为时间字符串(MM:SS:MS)"""

# 剪映中的时间单位是微秒

total\_seconds = microseconds / 1000000

minutes = int(total\_seconds // 60)

seconds = int(total\_seconds % 60)

ms = int((total\_seconds % 1) \* 1000)

return f"{minutes:02d}:{seconds:02d}:{ms:03d}"

def format\_duration(microseconds):

"""格式化持续时间为秒"""

return f"{microseconds/1000000:.2f}秒"

def find\_images\_in\_folder(folder\_path=None):

"""

在指定文件夹中查找图片文件

Args:

folder\_path: 图片文件夹路径，如果为None，则使用默认路径

Returns:

图片文件路径列表

"""

if folder\_path is None:

# 默认在桌面上查找图片文件夹

folder\_path = os.path.expanduser("~/Desktop/Youtube/images")

# 支持的图片格式

image\_extensions = \['jpg', 'jpeg', 'png', 'gif', 'webp'\]

# 查找所有图片文件

image\_files = \[\]

for ext in image\_extensions:

pattern = os.path.join(folder\_path, f"\*.{ext}")

image\_files.extend(glob(pattern))

if not image\_files:

# 如果没有找到图片，尝试在当前目录查找

current\_folder = os.path.dirname(os.path.abspath(\_\_file\_\_))

for ext in image\_extensions:

pattern = os.path.join(current\_folder, f"\*.{ext}")

image\_files.extend(glob(pattern))

if not image\_files:

raise Exception(f"未找到图片文件，请确保图片文件夹中包含图片")

return image\_files

def import\_images\_to\_draft(draft, image\_files):

"""

将图片导入到草稿中

Args:

draft: 剪映草稿JSON对象

image\_files: 图片文件路径列表

Returns:

更新后的草稿JSON对象，以及导入的图片材料列表

"""

# 确保materials中有videos键

if 'materials' not in draft:

draft\['materials'\] = {}

if 'videos' not in draft\['materials'\]:

draft\['materials'\]\['videos'\] = \[\]

# 导入图片

for image\_file in image\_files:

# 生成唯一ID

image\_id = str(uuid.uuid4())

# 获取文件名（不包含扩展名）

file\_name = os.path.basename(image\_file)

name, \_ = os.path.splitext(file\_name)

# 创建图片材料（作为视频材料存储）

image\_material = {

"aigc\_type": "none",

"audio\_fade": None,

"cartoon\_path": "",

"category\_id": "",

"category\_name": "",

"check\_flag": 63487,

"crop": {

"lower\_left\_x": 0.0,

"lower\_left\_y": 1.0,

"lower\_right\_x": 1.0,

"lower\_right\_y": 1.0,

"upper\_left\_x": 0.0,

"upper\_left\_y": 0.0,

"upper\_right\_x": 1.0,

"upper\_right\_y": 0.0

},

"crop\_ratio": "free",

"crop\_scale": 1.0,

"duration": 10800000000,

"extra\_type\_option": 0,

"formula\_id": "",

"freeze": None,

"has\_audio": False,

"height": 1080,

"id": image\_id,

"intensifies\_audio\_path": "",

"intensifies\_path": "",

"is\_ai\_generate\_content": False,

"is\_copyright": False,

"is\_text\_edit\_overdub": False,

"is\_unified\_beauty\_mode": False,

"local\_id": "",

"local\_material\_id": "",

"material\_id": "",

"material\_name": file\_name,

"material\_url": "",

"matting": {

"flag": 0,

"has\_use\_quick\_brush": False,

"has\_use\_quick\_eraser": False,

"interactiveTime": \[\],

"path": "",

"strokes": \[\]

},

"media\_path": "",

"object\_locked": None,

"origin\_material\_id": "",

"path": image\_file,

"picture\_from": "none",

"picture\_set\_category\_id": "",

"picture\_set\_category\_name": "",

"request\_id": "",

"reverse\_intensifies\_path": "",

"reverse\_path": "",

"smart\_motion": None,

"source": 0,

"source\_platform": 0,

"stable": {

"matrix\_path": "",

"stable\_level": 0,

"time\_range": {

"duration": 0,

"start": 0

}

},

"team\_id": "",

"type": "photo",

"video\_algorithm": {

"algorithms": \[\],

"complement\_frame\_config": None,

"deflicker": None,

"gameplay\_configs": \[\],

"motion\_blur\_config": None,

"noise\_reduction": None,

"path": "",

"quality\_enhance": None,

"time\_range": None

},

"width": 1920

}

# 添加到草稿中

draft\['materials'\]\['videos'\].append(image\_material)

print(f"已导入 {len(image\_files)} 个图片到草稿")

return draft

def create\_common\_keyframes(start\_time, duration, movement\_type=None):

"""创建关键帧数据"""

if movement\_type is None:

movement\_type = random.choice(\['left', 'right', 'up', 'down'\])

if movement\_type in \['left', 'right'\]:

# X轴移动，Y轴保持0

x\_start = -0.21 if movement\_type == 'left' else 0.21

x\_end = -x\_start # 反向移动

return \[\
\
{\
\
"id": str(uuid.uuid4()),\
\
"keyframe\_list": \[\
\
{"time\_offset": 0, "values": \[x\_start\]},\
\
{"time\_offset": duration, "values": \[x\_end\]}\
\
\],\
\
"property\_type": "KFTypePositionX"\
\
},\
\
{\
\
"id": str(uuid.uuid4()),\
\
"keyframe\_list": \[\
\
{"time\_offset": 0, "values": \[0\]},\
\
{"time\_offset": duration, "values": \[0\]}\
\
\],\
\
"property\_type": "KFTypePositionY"\
\
}\
\
\]

else:

# Y轴移动，X轴保持0

y\_start = -0.21 if movement\_type == 'up' else 0.21

y\_end = -y\_start # 反向移动

return \[\
\
{\
\
"id": str(uuid.uuid4()),\
\
"keyframe\_list": \[\
\
{"time\_offset": 0, "values": \[0\]},\
\
{"time\_offset": duration, "values": \[0\]}\
\
\],\
\
"property\_type": "KFTypePositionX"\
\
},\
\
{\
\
"id": str(uuid.uuid4()),\
\
"keyframe\_list": \[\
\
{"time\_offset": 0, "values": \[y\_start\]},\
\
{"time\_offset": duration, "values": \[y\_end\]}\
\
\],\
\
"property\_type": "KFTypePositionY"\
\
}\
\
\]

def create\_fade\_animation():

"""创建渐显动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 700000, # 0.7秒\
\
"id": "624705",\
\
"material\_type": "video",\
\
"name": "渐显",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/624705/00162fa64b6f03d941fea852a0054bc7",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6798320778182922760",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"type": "sticker\_animation"

}

def create\_scale\_animation():

"""创建缩放动画（向右甩入）"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 700000,\
\
"id": "431636",\
\
"material\_type": "video",\
\
"name": "向右甩入",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/431636/c83f7d144853d115a9e8572e667c6bfe",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6739338727866241539",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_bounce\_animation():

"""创建弹跳动画（向左滑动）"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 700000,\
\
"id": "624747",\
\
"material\_type": "video",\
\
"name": "向左滑动",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/624747/4f9fea978322067343df1b0fdb80798c",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6798332871267324423",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_wiper\_animation():

"""创建雨刷动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 700000,\
\
"id": "640101",\
\
"material\_type": "video",\
\
"name": "雨刷 II",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/640101/1241565fd010e8221475def8ab1a2f57",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6805748897768542727",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_shake\_animation():

"""创建抖动动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 700000,\
\
"id": "431654",\
\
"material\_type": "video",\
\
"name": "左右抖动",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/431654/267653b22765bd8348dda092f8de3cfe",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6739418540421419524",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_zoom\_in\_animation():

"""创建动感放大动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 500000,\
\
"id": "431662",\
\
"material\_type": "video",\
\
"name": "动感放大",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/431662/8fb560c01e4ccffbc4dc084f9c418838",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6740867832570974733",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_zoom\_out\_animation():

"""创建缩小动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 500000,\
\
"id": "624755",\
\
"material\_type": "video",\
\
"name": "缩小",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/624755/7cc60a6c2411194697a2b6e923844bca",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6798332584276267527",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_gentle\_shake\_animation():

"""创建轻微抖动动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 500000,\
\
"id": "431664",\
\
"material\_type": "video",\
\
"name": "轻微抖动",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/431664/944c5561f3d23baa068cee2bba4f15f5",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6739418227031413256",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_pendulum\_animation():

"""创建钟摆动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 500000,\
\
"id": "636115",\
\
"material\_type": "video",\
\
"name": "钟摆",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/636115/fb435c67390b89386c35e8b84f50faba",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "6803260897117606414",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

def create\_flip\_in\_animation():

"""创建翻入动画"""

animation\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"animations": \[\
\
{\
\
"anim\_adjust\_params": None,\
\
"category\_id": "in",\
\
"category\_name": "入场",\
\
"duration": 1170000,\
\
"id": "98430529",\
\
"material\_type": "video",\
\
"name": "翻入",\
\
"panel": "video",\
\
"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/98430529/bd0a96cbfbb58eb67c5f4e86f537b858",\
\
"platform": "all",\
\
"request\_id": request\_id,\
\
"resource\_id": "7452407076417966619",\
\
"start": 0,\
\
"type": "in"\
\
}\
\
\],

"id": animation\_id,

"multi\_language\_current": "none",

"type": "sticker\_animation"

}

\# 全局变量，用于记录上一次使用的动画

last\_animation = None

def get\_random\_animation():

"""随机选择一个动画效果，确保不会连续使用相同的动画"""

global last\_animation

# 所有可用的动画效果函数列表

animations = \[\
\
create\_fade\_animation,\
\
create\_scale\_animation,\
\
create\_bounce\_animation,\
\
create\_wiper\_animation,\
\
create\_shake\_animation,\
\
create\_zoom\_in\_animation,\
\
create\_zoom\_out\_animation,\
\
create\_gentle\_shake\_animation,\
\
create\_pendulum\_animation,\
\
create\_flip\_in\_animation\
\
\]

# 从列表中移除上一次使用的动画

if last\_animation and last\_animation in animations:

available\_animations = \[anim for anim in animations if anim != last\_animation\]

else:

available\_animations = animations

# 随机选择一个动画

chosen\_animation = random.choice(available\_animations)

last\_animation = chosen\_animation

return chosen\_animation()

def find\_next\_subtitle\_time(subtitle\_segments, current\_start\_time):

"""

找到当前图片应该结束的时间点:

1\. 先确定最早可能结束的时间点 = 当前开始时间 + 5秒

2\. 然后找到在这个时间点之后的第一个字幕开始时间

Args:

subtitle\_segments: 字幕片段列表

current\_start\_time: 当前图片的开始时间（微秒）

Returns:

下一个字幕的开始时间，或者当前开始时间+5秒

"""

min\_possible\_end = current\_start\_time + 5000000 # 当前图片最早可能结束的时间(5秒)

print(f"当前图片开始时间: {microsec\_to\_time(current\_start\_time)}")

print(f"当前图片最早可能结束时间(+5秒): {microsec\_to\_time(min\_possible\_end)}")

# 找到第一个开始时间大于min\_possible\_end的字幕

for subtitle in subtitle\_segments:

subtitle\_start = subtitle\['target\_timerange'\]\['start'\]

if subtitle\_start > min\_possible\_end: # 只关心字幕的开始时间

print(f"找到下一个字幕时间: {microsec\_to\_time(subtitle\_start)}")

return subtitle\_start

# 如果没找到合适的字幕,就用最小结束时间

print(f"没找到更晚的字幕,使用最小结束时间: {microsec\_to\_time(min\_possible\_end)}")

return min\_possible\_end

def add\_effects\_to\_segment(segment):

"""

为片段添加特效

Args:

segment: 片段对象

Returns:

更新后的片段对象

"""

# 添加一些基本特效

effects = \[\
\
# 可以在这里添加其他特效ID\
\
"E312DFCC-91BF-47D1-831A-999CE06AF820", # 速度特效\
\
"BAE4FFEE-2A02-4D91-9C10-1CFA0B5A9FA7" # 画布特效\
\
\]

# 添加特效引用

segment\["extra\_material\_refs"\] = effects

return segment

def create\_star\_effect():

"""创建星火特效"""

effect\_id = str(uuid.uuid4())

return {

"adjust\_params": \[\
\
{"default\_value": 0.33, "name": "effects\_adjust\_speed", "value": 0.33},\
\
{"default\_value": 1.0, "name": "effects\_adjust\_background\_animation", "value": 1.0}\
\
\],

"algorithm\_artifact\_path": "",

"apply\_target\_type": 2,

"apply\_time\_range": None,

"category\_id": "39654",

"category\_name": "热门",

"common\_keyframes": \[\],

"disable\_effect\_faces": \[\],

"effect\_id": "634103",

"formula\_id": "",

"id": effect\_id,

"name": "星火",

"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/634103/c2811a4bdeb4394ae95f3aa9875dc4dc",

"platform": "all",

"render\_index": 0,

"request\_id": "",

"resource\_id": "6715209198109463054",

"source\_platform": 0,

"time\_range": None,

"track\_render\_index": 0,

"type": "video\_effect",

"value": 1.0,

"version": ""

}

def create\_firefly\_effect():

"""创建萤火特效"""

effect\_id = str(uuid.uuid4())

return {

"adjust\_params": \[\
\
{"default\_value": 0.33, "name": "effects\_adjust\_speed", "value": 0.33},\
\
{"default\_value": 1.0, "name": "effects\_adjust\_background\_animation", "value": 1.0}\
\
\],

"algorithm\_artifact\_path": "",

"apply\_target\_type": 2,

"apply\_time\_range": None,

"category\_id": "39654",

"category\_name": "热门",

"common\_keyframes": \[\],

"disable\_effect\_faces": \[\],

"effect\_id": "1357502",

"formula\_id": "",

"id": effect\_id,

"name": "萤火",

"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1357502/d473ca7fa127312a7651ec1523a6e880",

"platform": "all",

"render\_index": 0,

"request\_id": "",

"resource\_id": "7006265184050221576",

"source\_platform": 0,

"time\_range": None,

"track\_render\_index": 0,

"type": "video\_effect",

"value": 1.0,

"version": ""

}

def create\_gold\_dust\_effect():

"""创建金粉闪闪特效"""

effect\_id = str(uuid.uuid4())

request\_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4())\[:8\].upper()

return {

"adjust\_params": \[\
\
{"default\_value": 0.3361999988555908, "name": "effects\_adjust\_speed", "value": 0.3361999988555908},\
\
{"default\_value": 0.5, "name": "effects\_adjust\_filter", "value": 0.5},\
\
{"default\_value": 1.0, "name": "effects\_adjust\_background\_animation", "value": 1.0}\
\
\],

"algorithm\_artifact\_path": "",

"apply\_target\_type": 2,

"apply\_time\_range": None,

"category\_id": "107",

"category\_name": "收藏",

"common\_keyframes": \[\],

"disable\_effect\_faces": \[\],

"effect\_id": "1453820",

"formula\_id": "",

"id": effect\_id,

"name": "金粉闪闪",

"path": "/Users/a47/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1453820/a552dfa820b5aba27e4f09e3d83b8643",

"platform": "all",

"render\_index": 0,

"request\_id": request\_id,

"resource\_id": "7034048554318434830",

"source\_platform": 0,

"time\_range": None,

"track\_render\_index": 0,

"type": "video\_effect",

"value": 1.0,

"version": ""

}

def add\_effect\_track(draft, segments):

"""添加特效轨道"""

# 创建特效轨道

effect\_track = {

"attribute": 0,

"flag": 0,

"id": str(uuid.uuid4()),

"is\_default\_name": True,

"name": "",

"segments": \[\],

"type": "effect"

}

# 为每个视频片段创建对应的特效

for i, segment in enumerate(segments):

start\_time = segment\['target\_timerange'\]\['start'\]

duration = segment\['target\_timerange'\]\['duration'\]

# 随机选择一个特效

effect\_funcs = \[create\_star\_effect, create\_firefly\_effect, create\_gold\_dust\_effect\]

effect = random.choice(effect\_funcs)()

# 添加特效到materials

if 'video\_effects' not in draft\['materials'\]:

draft\['materials'\]\['video\_effects'\] = \[\]

draft\['materials'\]\['video\_effects'\].append(effect)

# 创建特效片段

effect\_segment = {

"caption\_info": None,

"cartoon": False,

"clip": None,

"common\_keyframes": \[\],

"enable\_adjust": False,

"enable\_color\_curves": True,

"enable\_color\_match\_adjust": False,

"enable\_color\_wheels": True,

"enable\_lut": False,

"enable\_smart\_color\_adjust": False,

"extra\_material\_refs": \[\],

"group\_id": "",

"id": str(uuid.uuid4()),

"intensifies\_audio": False,

"is\_placeholder": False,

"is\_tone\_modify": False,

"keyframe\_refs": \[\],

"last\_nonzero\_volume": 1.0,

"material\_id": effect\['id'\],

"render\_index": 11000 + i,

"responsive\_layout": {

"enable": False,

"horizontal\_pos\_layout": 0,

"size\_layout": 0,

"target\_follow": "",

"vertical\_pos\_layout": 0

},

"reverse": False,

"source\_timerange": None,

"speed": 1.0,

"target\_timerange": {

"duration": duration,

"start": start\_time

},

"template\_id": "",

"template\_scene": "default",

"track\_attribute": 0,

"track\_render\_index": 1,

"uniform\_scale": None,

"visible": True,

"volume": 1.0

}

effect\_track\['segments'\].append(effect\_segment)

return effect\_track

def sync\_images\_with\_subtitles\_in\_draft(draft):

"""

在草稿中将图片与字幕同步

Args:

draft: 剪映草稿JSON对象

Returns:

更新后的草稿JSON对象

"""

# 查找文本轨道

text\_track = None

for track in draft.get('tracks', \[\]):

if track.get('type') == 'text':

text\_track = track

print("找到text轨道")

break

if not text\_track:

print("未找到text轨道，无法同步图片与字幕")

return draft

# 获取所有字幕片段

subtitle\_segments = text\_track.get('segments', \[\])

print(f"找到 {len(subtitle\_segments)} 个字幕片段")

# 打印字幕时间范围

print("字幕时间范围:")

for i, subtitle in enumerate(subtitle\_segments):

subtitle\_start = subtitle\['target\_timerange'\]\['start'\]

subtitle\_end = subtitle\_start + subtitle\['target\_timerange'\]\['duration'\]

subtitle\_duration = subtitle\['target\_timerange'\]\['duration'\] / 1000000

print(f" 字幕 {i}: 开始={microsec\_to\_time(subtitle\_start)}, 结束={microsec\_to\_time(subtitle\_end)}, 持续={subtitle\_duration:.2f}秒秒")

# 查找图片轨道

image\_track = None

for track in draft.get('tracks', \[\]):

if track.get('type') == 'video':

# 检查是否有图片材料

has\_image = False

for segment in track.get('segments', \[\]):

material\_id = segment.get('material\_id', '')

material = None

for mat in draft.get('materials', {}).get('videos', \[\]):

if mat.get('id') == material\_id:

material = mat

break

# 在剪映中，图片类型可能是'photo'或'image'

if material and (material.get('type') == 'photo' or material.get('type') == 'image'):

has\_image = True

break

if has\_image:

image\_track = track

print("使用现有的图片轨道")

break

if not image\_track:

# 创建新的图片轨道

image\_track = {

"attribute": 0,

"flag": 0,

"id": str(uuid.uuid4()),

"is\_default\_name": True,

"name": "",

"segments": \[\],

"type": "video"

}

draft\['tracks'\].append(image\_track)

print("创建了新的图片轨道")

# 获取所有图片材料 \- 在剪映中，图片类型是'photo'或'image'

image\_materials = \[\]

for video in draft.get('materials', {}).get('videos', \[\]):

if video.get('type') == 'photo' or video.get('type') == 'image':

image\_materials.append(video)

print(f"找到 {len(image\_materials)} 个图片材料")

# 如果没有找到图片材料，创建一个默认的图片材料

if not image\_materials:

print("未找到图片材料，将创建默认图片材料")

# 创建一个默认的图片材料

default\_image\_id = str(uuid.uuid4())

default\_image = {

"duration": 10800000000, # 使用与剪映草稿中相同的默认持续时间

"height": 1080,

"id": default\_image\_id,

"local\_material\_id": default\_image\_id,

"material\_name": "默认图片",

"path": "", # 这里应该填入一个实际的图片路径，但我们暂时留空

"type": "photo", # 使用'photo'类型与剪映一致

"width": 1920

}

# 添加到materials

if 'materials' not in draft:

draft\['materials'\] = {}

if 'videos' not in draft\['materials'\]:

draft\['materials'\]\['videos'\] = \[\]

draft\['materials'\]\['videos'\].append(default\_image)

image\_materials.append(default\_image)

print("已创建默认图片材料")

if len(image\_materials) < len(subtitle\_segments):

print(f"警告: 图片数量({len(image\_materials)})少于字幕数量({len(subtitle\_segments)})")

# 清空图片轨道的片段

image\_track\['segments'\] = \[\]

# 确保 materials 中有 material\_animations 列表

if 'materials' not in draft:

draft\['materials'\] = {}

if 'material\_animations' not in draft\['materials'\]:

draft\['materials'\]\['material\_animations'\] = \[\]

# 按照字幕顺序创建图片片段

last\_end\_time = 0 # 第一张图片从0开始

created\_segments = \[\]

for i in range(len(subtitle\_segments)):

# 当前图片的开始时间就是上一张图片的结束时间

start\_time = last\_end\_time

# 找到这张图片应该结束的时间

# 必须是某个字幕的开始时间,且至少要在start\_time+5秒之后

end\_time = find\_next\_subtitle\_time(subtitle\_segments, start\_time)

print(f"\\n当前图片开始时间: {microsec\_to\_time(start\_time)}")

print(f"当前图片最早可能结束时间(+5秒): {microsec\_to\_time(start\_time + 5000000)}")

print(f"找到下一个字幕时间: {microsec\_to\_time(end\_time)}")

# 计算持续时间

duration = end\_time - start\_time

# 选择图片材料 (如果图片不够，则循环使用)

image\_index = i % len(image\_materials)

image\_material = image\_materials\[image\_index\]

print(f"\\n图片 {i}:")

print(f"开始时间: {microsec\_to\_time(start\_time)}")

print(f"结束时间: {microsec\_to\_time(end\_time)}")

print(f"持续时间: {duration / 1000000:.2f}秒秒")

print(f"对应字幕: {microsec\_to\_time(start\_time)} - {microsec\_to\_time(end\_time)}")

# 创建图片片段

image\_segment = {

"cartoon": False,

"clip": {

"alpha": 1.0,

"flip": {"horizontal": False, "vertical": False},

"rotation": 0.0,

"scale": {"x": 1.25, "y": 1.25}, # 使用1.25的缩放比例，与英语字幕对齐.py一致

"transform": {"x": 0.0, "y": 0.0}

},

"common\_keyframes": \[\],

"enable\_adjust": False,

"enable\_color\_curves": True,

"enable\_color\_wheels": True,

"extra\_material\_refs": \[\],

"group\_id": "",

"id": str(uuid.uuid4()),

"intensifies\_audio": False,

"is\_placeholder": False,

"material\_id": image\_material\['id'\],

"render\_index": i,

"source\_timerange": {

"duration": duration,

"start": 0

},

"speed": 1.0,

"target\_timerange": {

"duration": duration,

"start": start\_time

},

"template\_id": "",

"template\_scene": "default",

"track\_attribute": 0,

"track\_render\_index": 0,

"uniform\_scale": {"on": True, "value": 1.0},

"visible": True,

"volume": 1.0

}

# 创建随机动画效果

animation = get\_random\_animation()

draft\['materials'\]\['material\_animations'\].append(animation)

# 添加动画引用到 extra\_material\_refs

image\_segment\['extra\_material\_refs'\].append(animation\['id'\])

# 设置关键帧

image\_segment\['common\_keyframes'\] = create\_common\_keyframes(start\_time, duration)

# 添加到图片轨道

image\_track\['segments'\].append(image\_segment)

created\_segments.append(image\_segment)

# 更新下一张图片的开始时间

last\_end\_time = end\_time

# 添加特效轨道

effect\_track = add\_effect\_track(draft, created\_segments)

draft\['tracks'\].append(effect\_track)

print(f"已添加 {len(created\_segments)} 个图片片段，并应用了关键帧和特效")

return draft

def process\_draft\_automatically():

"""

自动处理最新的剪映草稿，同步图片与字幕

Returns:

None

"""

try:

# 获取最新的草稿文件夹

latest\_draft\_folder = get\_latest\_draft\_folder()

print(f"找到最新草稿文件夹: {latest\_draft\_folder}")

# 读取draft\_content.json

draft\_content\_path = os.path.join(latest\_draft\_folder, 'draft\_content.json')

with open(draft\_content\_path, 'r', encoding='utf-8') as f:

draft = json.load(f)

# 同步图片与字幕

draft = sync\_images\_with\_subtitles\_in\_draft(draft)

# 保存修改后的draft\_content.json

with open(draft\_content\_path, 'w', encoding='utf-8') as f:

json.dump(draft, f, ensure\_ascii=False)

print(f"成功将图片与字幕同步到草稿: {latest\_draft\_folder}")

except Exception as e:

print(f"处理草稿时出错: {str(e)}")

if \_\_name\_\_ == "\_\_main\_\_":

# 直接处理草稿，不需要用户输入

process\_draft\_automatically()
