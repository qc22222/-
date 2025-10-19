import os

import requests

import json

import string

import time

from docx import Document

from datetime import datetime, timedelta

import azure.cognitiveservices.speech as speechsdk

from pathlib import Path

import subprocess

from tqdm import tqdm

import whisper

import torch

import shutil

import tarfile

import io

from pydub import AudioSegment

class TTSGenerator:

def convert\_json\_to\_srt(self, subtitle\_data, output\_file):

"""将MiniMax返回的JSON字幕转换为SRT格式"""

try:

# 检查字幕数据格式

if not isinstance(subtitle\_data, list):

self.log\_message("字幕数据格式不正确，应为列表", "ERROR")

return False

# 记录字幕数据的第一项，用于调试

if subtitle\_data:

self.log\_message(f"字幕数据第一项: {json.dumps(subtitle\_data\[0\], ensure\_ascii=False)}")

srt\_content = \[\]

for i, item in enumerate(subtitle\_data, 1):

# 检查各种可能的字段名称

# 开始时间字段可能的名称

start\_time\_field = None

for field in \['start\_time', 'begin\_time', 'start', 'begin', 'startTime', 'beginTime', 'time\_begin'\]:

if field in item:

start\_time\_field = field

break

# 结束时间字段可能的名称

end\_time\_field = None

for field in \['end\_time', 'finish\_time', 'end', 'finish', 'endTime', 'finishTime', 'time\_end'\]:

if field in item:

end\_time\_field = field

break

# 文本内容字段可能的名称

text\_field = None

for field in \['text', 'content', 'subtitle', 'words', 'sentence'\]:

if field in item:

text\_field = field

break

# 如果缺少任何必要字段，则跳过此条目

if not start\_time\_field or not end\_time\_field or not text\_field:

self.log\_message(f"跳过字幕条目，缺少必要字段: {json.dumps(item, ensure\_ascii=False)}", "WARNING")

continue

# 获取开始和结束时间（毫秒）

start\_ms = item\[start\_time\_field\]

end\_ms = item\[end\_time\_field\]

text = item\[text\_field\]

# 检查时间格式是否为数字（毫秒）

if not isinstance(start\_ms, (int, float)):

self.log\_message(f"开始时间不是数字: {start\_ms}", "WARNING")

# 尝试将字符串转换为数字

try:

start\_ms = float(start\_ms)

except:

continue

if not isinstance(end\_ms, (int, float)):

self.log\_message(f"结束时间不是数字: {end\_ms}", "WARNING")

# 尝试将字符串转换为数字

try:

end\_ms = float(end\_ms)

except:

continue

# 转换为SRT时间格式 (HH:MM:SS,mmm)

start\_time = self.ms\_to\_srt\_time(start\_ms)

end\_time = self.ms\_to\_srt\_time(end\_ms)

# 添加SRT条目

srt\_entry = f"{i}\\n{start\_time} --> {end\_time}\\n{text}\\n"

srt\_content.append(srt\_entry)

# 写入SRT文件

with open(output\_file, 'w', encoding='utf-8') as f:

f.write('\\n'.join(srt\_content))

# 记录生成的SRT内容长度

self.log\_message(f"生成的SRT文件包含 {len(srt\_content)} 条字幕")

return True

except Exception as e:

self.log\_message(f"转换字幕格式失败: {str(e)}", "ERROR")

return False

def ms\_to\_srt\_time(self, milliseconds):

"""将毫秒转换为SRT时间格式 (HH:MM:SS,mmm)"""

# 确保毫秒是整数

milliseconds = float(milliseconds) # 先转换为浮点数以确保兼容性

seconds, ms = divmod(milliseconds, 1000)

minutes, seconds = divmod(int(seconds), 60)

hours, minutes = divmod(int(minutes), 60)

# 确保 ms 是整数

ms = int(ms)

return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{ms:03d}"

def srt\_time\_to\_ms(self, time\_str):

"""将SRT时间格式转换为毫秒

Args:

time\_str: SRT时间格式字符串，例如 "00:00:01,500"

Returns:

毫秒数

"""

try:

# 分离时、分、秒和毫秒

main\_part, ms\_part = time\_str.split(',')

h, m, s = main\_part.split(':')

# 转换为毫秒

total\_ms = int(h) \* 3600000 + int(m) \* 60000 + int(s) \* 1000 + int(ms\_part)

return total\_ms

except Exception as e:

self.log\_message(f"SRT时间格式转换失败: {str(e)}", "ERROR")

return 0

def split\_subtitle\_text(self, text):

"""将字幕文本按照要求切割，每句话最长不超过13个字

如果第13个字是中文字符，则向后寻找第一个标点符号，在符号处切割"""

if not text or len(text) <= 13:

return \[text\]

# 中文标点符号列表

punctuations = \['，', '。', '、', '；', '：', '？', '！', '…', '"', '"', ''', ''', '）', '】', '》', '」', '』', '〕', '｝', '］'\]

# 添加英文标点

punctuations.extend(\[',', '.', ';', ':', '?', '!', ')', '\]', '}'\])

result = \[\]

start = 0

while start < len(text):

# 如果剩余文本长度小于等于13，直接添加并结束

if len(text) - start <= 13:

result.append(text\[start:\])

break

# 初始切割点设为start+13

cut\_point = start + 13

# 检查第13个字符是否是中文

is\_chinese = '\\u4e00' <= text\[cut\_point\] <= '\\u9fff'

if is\_chinese:

# 向后查找最近的标点符号

found\_punct = False

for i in range(cut\_point, min(cut\_point + 10, len(text))):

if text\[i\] in punctuations:

# 在标点符号后切割

cut\_point = i + 1

found\_punct = True

break

# 如果没找到标点符号但已经接近文本末尾，直接取剩余文本

if not found\_punct and len(text) - cut\_point < 5:

cut\_point = len(text)

# 添加切割后的文本

result.append(text\[start:cut\_point\])

start = cut\_point

return result

def optimize\_srt\_file(self, srt\_file\_path):

"""优化SRT文件，将长字幕切割成短字幕"""

try:

self.log\_message(f"开始优化SRT文件: {srt\_file\_path}")

# 读取原始SRT文件

with open(srt\_file\_path, 'r', encoding='utf-8') as f:

content = f.read()

# 解析SRT内容

srt\_blocks = content.strip().split('\\n\\n')

new\_blocks = \[\]

new\_index = 1

for block in srt\_blocks:

lines = block.strip().split('\\n')

if len(lines) < 3:

self.log\_message(f"跳过无效的SRT块: {block}", "WARNING")

continue

# 提取时间轴和文本

try:

index = int(lines\[0\])

time\_line = lines\[1\]

text = '\\n'.join(lines\[2:\])

# 解析时间

time\_parts = time\_line.split(' --> ')

if len(time\_parts) != 2:

self.log\_message(f"无效的时间轴格式: {time\_line}", "WARNING")

new\_blocks.append(block)

continue

start\_time, end\_time = time\_parts

# 切割字幕文本

split\_texts = self.split\_subtitle\_text(text)

if len(split\_texts) == 1:

# 如果没有切割，保持原样

new\_blocks.append(f"{new\_index}\\n{time\_line}\\n{text}")

new\_index += 1

else:

# 计算每段字幕的时间

start\_ms = self.srt\_time\_to\_ms(start\_time)

end\_ms = self.srt\_time\_to\_ms(end\_time)

total\_duration = end\_ms - start\_ms

segment\_duration = total\_duration / len(split\_texts)

# 为每个切割后的文本创建新的字幕块

for i, segment\_text in enumerate(split\_texts):

segment\_start\_ms = start\_ms + i \* segment\_duration

segment\_end\_ms = segment\_start\_ms + segment\_duration

segment\_start\_time = self.ms\_to\_srt\_time(segment\_start\_ms)

segment\_end\_time = self.ms\_to\_srt\_time(segment\_end\_ms)

new\_blocks.append(f"{new\_index}\\n{segment\_start\_time} --> {segment\_end\_time}\\n{segment\_text}")

new\_index += 1

except Exception as e:

self.log\_message(f"处理SRT块时出错: {str(e)}", "ERROR")

# 保留原始块

new\_blocks.append(block)

# 写入优化后的SRT文件

optimized\_content = '\\n\\n'.join(new\_blocks)

with open(srt\_file\_path, 'w', encoding='utf-8') as f:

f.write(optimized\_content)

self.log\_message(f"SRT文件优化完成: {srt\_file\_path}")

return True

except Exception as e:

self.log\_message(f"优化SRT文件失败: {str(e)}", "ERROR")

return False

def \_\_init\_\_(self):

# 设置Azure SDK的日志级别为最高级别以禁用所有日志

import logging

logging.getLogger('azure').setLevel(logging.CRITICAL)

logging.getLogger('websockets').setLevel(logging.CRITICAL)

# 基础配置

from pathlib import Path

self.desktop\_path = str(Path.home() / "Desktop")

# 更新路径以匹配新的文件夹结构

self.rewrite\_path = os.path.join(self.desktop\_path, "Youtube/改写")

# MiniMax API配置

self.minimax\_api\_key = ""

self.minimax\_group\_id = ""

# Azure TTS配置

self.azure\_subscription\_key = ""

self.azure\_region = ""

self.azure\_voice\_name = ""

# Whisper模型配置

self.whisper\_model = "small" # 默认使用small模型，平衡速度和准确度

# 初始化Azure语音配置

try:

self.speech\_config = speechsdk.SpeechConfig(

subscription=self.azure\_subscription\_key,

region=self.azure\_region

)

self.speech\_config.set\_speech\_synthesis\_output\_format(

speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3

)

self.speech\_config.speech\_synthesis\_voice\_name = self.azure\_voice\_name

except Exception as e:

self.log\_message(f"初始化Azure TTS失败: {str(e)}", "ERROR")

self.speech\_config = None

# 初始化文件选择和模式

self.selected\_files = \[\]

self.file\_modes = {}

self.current\_mode = None

# 选择Whisper模型

self.select\_whisper\_model()

# 开始处理文件

self.select\_and\_process\_files()

def select\_whisper\_model(self):

"""选择Whisper模型大小"""

print("\\n=== 选择Whisper语音识别模型 ===")

print("可用的模型大小:")

print("1. tiny - 最小的模型，速度最快但准确度最低")

print("2. base - 小型模型，速度较快，准确度适中")

print("3. small - 中型模型，平衡了速度和准确度（默认）")

print("4. medium - 较大模型，准确度高，速度较慢")

print("5. large - 最大的模型，准确度最高，但速度最慢")

while True:

choice = input("\\n请选择模型大小 (1-5，默认3): ").strip()

if not choice:

self.whisper\_model = "small" # 默认

break

try:

choice\_num = int(choice)

if 1 <= choice\_num <= 5:

models = \["tiny", "base", "small", "medium", "large"\]

self.whisper\_model = models\[choice\_num - 1\]

break

else:

print("请输入1到5之间的数字")

except ValueError:

print("请输入有效的数字")

self.log\_message(f"已选择Whisper模型: {self.whisper\_model}")

def select\_and\_process\_files(self):

"""选择并处理文件"""

# 获取可用文件列表

docx\_files = self.get\_docx\_files()

if not docx\_files:

self.log\_message("没有找到可用文件", "ERROR")

return

# 显示文件列表

self.log\_message("\\n可用文件:")

for i, file in enumerate(docx\_files, 1):

self.log\_message(f"{i}. {file}")

# 文件选择循环

self.log\_message("\\n请选择文件编号（多个文件用空格分隔）: ", "INFO")

file\_input = input().strip()

try:

# 解析输入的文件编号

indices = \[int(idx) - 1 for idx in file\_input.split()\]

# 检查每个编号的有效性

valid\_indices = \[idx for idx in indices if 0 <= idx < len(docx\_files)\]

# 显示无效的选择

invalid\_indices = \[idx + 1 for idx in indices if idx not in valid\_indices\]

if invalid\_indices:

self.log\_message(f"无效的文件编号: {', '.join(map(str, invalid\_indices))}", "ERROR")

return

# 获取要处理的文件

files\_to\_process = \[docx\_files\[idx\] for idx in valid\_indices\]

if not files\_to\_process:

self.log\_message("未选择任何有效文件", "ERROR")

return

# 为每个文件选择模式

for file\_name in files\_to\_process:

self.log\_message(f"\\n为文件 {file\_name} 选择模式:")

self.select\_mode(file\_name)

self.selected\_files.append(file\_name)

# 开始处理文件

self.log\_message("\\n开始处理选中的文件...")

self.process\_files() # 只调用一次

except ValueError:

self.log\_message("输入无效，请输入数字编号", "ERROR")

def display\_available\_files(self, docx\_files):

"""显示可用文件列表，标记已选择的文件"""

self.log\_message("\\n可用文件列表 (已选择的文件已标记):")

for i, file in enumerate(docx\_files, 1):

status = " \[已选择\]" if file in self.selected\_files else ""

self.log\_message(f"{i}. {file}{status}")

def select\_mode(self, file\_name):

"""为文件选择处理模式"""

while True:

if self.speech\_config is None:

self.log\_message("1: 通用声音\\n2: 奇幻声音\\n请选择(1-2): ", "INFO")

mode\_input = input().strip()

try:

mode = int(mode\_input)

if 1 <= mode <= 2:

self.file\_modes\[file\_name\] = mode

break

except ValueError:

pass

else:

self.log\_message("1: 通用声音\\n2: 奇幻声音\\n3: Azure TTS\\n4: 墨西哥西班牙语 (Jorge)\\n请选择(1-4): ", "INFO")

mode\_input = input().strip()

try:

mode = int(mode\_input)

if 1 <= mode <= 4:

self.file\_modes\[file\_name\] = mode

break

except ValueError:

pass

self.log\_message("请输入有效的数字")

def split\_text(self, text):

"""按照标点符号分割文本，保持每段的完整性"""

# 去除多余的空白字符

text = ' '.join(text.split())

# 初始化结果列表

segments = \[\]

current\_segment = ""

# 遍历文本

for char in text:

current\_segment += char

# 当遇到分隔符时，保存当前段落

if char in \['.', ',', '。', '，'\]:

# 去掉末尾的标点

clean\_segment = current\_segment\[:-1\].strip()

if clean\_segment:

segments.append(clean\_segment)

current\_segment = ""

# 处理最后一段

if current\_segment.strip():

segments.append(current\_segment.strip())

return \[s for s in segments if s\]

def generate\_srt(self, segments, start\_time=0):

"""生成标准格式的SRT文件内容"""

srt\_content = \[\]

current\_time = start\_time

for i, segment in enumerate(segments, 1):

# 计算持续时间（基于文本长度，每个字约0.3秒）

duration = len(segment) \* 0.3

duration = max(1.5, min(duration, 5)) # 最短1.5秒，最长5秒

# 格式化时间戳

start = self.format\_timestamp(current\_time)

end = self.format\_timestamp(current\_time + duration)

# 添加SRT条目（确保每个部分都有换行）

srt\_content.append(f"{i}\\n{start} --> {end}\\n{segment}\\n")

# 更新下一段的开始时间（添加0.1秒间隔）

current\_time += duration + 0.1

return "\\n".join(srt\_content)

def format\_timestamp(self, seconds):

"""将秒数转换为 SRT 格式的时间戳"""

hours = int(seconds // 3600)

minutes = int((seconds % 3600) // 60)

secs = int(seconds % 60)

msecs = int((seconds \* 1000) % 1000)

return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"

def get\_current\_time(self):

"""获取当前时间的格式化字符串"""

return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log\_message(self, message, level="INFO"):

"""输出日志信息"""

print(f"\[{self.get\_current\_time()}\] \[{level}\] {message}")

def read\_docx(self, display\_name):

"""从改写文件夹读取指定的文件内容"""

try:

# 从映射中获取原始文件名

original\_file = self.file\_mapping.get(display\_name)

if not original\_file:

self.log\_message(f"找不到文件映射: {display\_name}", "ERROR")

return None

file\_path = os.path.join(self.rewrite\_path, original\_file)

if not os.path.exists(file\_path):

self.log\_message(f"文件不存在: {file\_path}", "ERROR")

return None

# 根据文件类型读取内容

if file\_path.endswith('.docx'):

doc = Document(file\_path)

text = \[\]

for paragraph in doc.paragraphs:

if paragraph.text.strip(): # 只添加非空段落

text.append(paragraph.text.strip())

return '\\n'.join(text)

elif file\_path.endswith('.txt'):

# 读取文本文件

with open(file\_path, 'r', encoding='utf-8') as f:

return f.read().strip()

else:

self.log\_message(f"不支持的文件格式: {file\_path}", "ERROR")

return None

except Exception as e:

self.log\_message(f"读取文件失败: {str(e)}", "ERROR")

return None

def download\_file(self, file\_id, output\_file):

"""下载文件"""

try:

# 先获取文件信息

retrieve\_url = f"https://api.minimax.chat/v1/files/retrieve?GroupId={self.minimax\_group\_id}&file\_id={file\_id}"

headers = {

"Authorization": f"Bearer {self.minimax\_api\_key}",

"Content-Type": "application/json"

}

response = requests.get(retrieve\_url, headers=headers)

response.raise\_for\_status()

data = response.json()

if "base\_resp" not in data or data\["base\_resp"\]\["status\_code"\] != 0:

error\_msg = data.get("base\_resp", {}).get("status\_msg", "未知错误")

self.log\_message(f"获取文件信息失败: {error\_msg}", "ERROR")

return False

# 获取下载链接

file\_info = data.get("file", {})

download\_url = file\_info.get("download\_url")

if not download\_url:

self.log\_message("未能获取下载链接", "ERROR")

return False

# 下载文件内容

download\_response = requests.get(

f"https://api.minimax.chat/v1/files/retrieve\_content?GroupId={self.minimax\_group\_id}&file\_id={file\_id}",

headers=headers

)

download\_response.raise\_for\_status()

# 保存文件

with open(output\_file, "wb") as f:

f.write(download\_response.content)

self.log\_message(f"文件已保存到: {output\_file}")

return True

except Exception as e:

self.log\_message(f"下载文件失败: {str(e)}", "ERROR")

return False

def call\_minimax\_api(self, text, output\_file, mode="normal", generate\_srt=True):

"""使用MiniMax API生成语音"""

self.log\_message("正在创建MiniMax语音合成任务...")

# 使用T2A V2 API，支持字幕生成

base\_url = "https://api.minimax.chat/v1/t2a\_v2"

headers = {

"Authorization": f"Bearer {self.minimax\_api\_key}",

"Content-Type": "application/json",

}

voice\_id = "audiobook\_male\_1" if mode == "normal" else "audiobook\_male\_2"

payload = {

"model": "speech-01-turbo",

"text": text,

"stream": False,

"subtitle\_enable": generate\_srt, # 启用字幕功能

"voice\_setting": {

"voice\_id": voice\_id,

"speed": 1,

"vol": 1,

"pitch": 0

},

"audio\_setting": {

"sample\_rate": 32000,

"bitrate": 128000,

"format": "mp3",

"channel": 2

}

}

try:

# 直接调用T2A V2 API（同步方式）

url = f"{base\_url}?GroupId={self.minimax\_group\_id}"

response = requests.post(url, headers=headers, json=payload)

response.raise\_for\_status()

result = response.json()

if "base\_resp" not in result or result\["base\_resp"\]\["status\_code"\] != 0:

error\_msg = result.get("base\_resp", {}).get("status\_msg", "未知错误")

self.log\_message(f"API请求失败: {error\_msg}", "ERROR")

return False

# 检查是否有音频数据

if "data" not in result or "audio" not in result\["data"\]:

self.log\_message("API返回中没有音频数据", "ERROR")

return False

# 获取音频数据（hex格式）

audio\_hex = result\["data"\]\["audio"\]

audio\_data = bytes.fromhex(audio\_hex)

# 保存音频文件

with open(output\_file, "wb") as f:

f.write(audio\_data)

self.log\_message(f"音频文件已保存到: {output\_file}")

# 处理字幕文件（如果有）

if generate\_srt and "subtitle\_file" in result:

subtitle\_url = result\["subtitle\_file"\]

self.log\_message(f"检测到字幕文件链接: {subtitle\_url}")

# 下载字幕文件（JSON格式）

try:

subtitle\_response = requests.get(subtitle\_url)

subtitle\_response.raise\_for\_status()

subtitle\_data = subtitle\_response.json()

# 输出字幕数据结构信息便于调试

self.log\_message(f"字幕数据类型: {type(subtitle\_data)}")

if isinstance(subtitle\_data, list):

self.log\_message(f"字幕条目数量: {len(subtitle\_data)}")

if len(subtitle\_data) > 0:

self.log\_message(f"第一条字幕数据结构: {subtitle\_data\[0\].keys() if isinstance(subtitle\_data\[0\], dict) else '非字典格式'}")

# 保存原始JSON字幕文件

json\_subtitle\_file = output\_file.rsplit(".", 1)\[0\] + ".json"

with open(json\_subtitle\_file, "w", encoding="utf-8") as f:

json.dump(subtitle\_data, f, ensure\_ascii=False, indent=2)

self.log\_message(f"JSON字幕文件已保存: {json\_subtitle\_file}")

# 转换为SRT格式并保存

srt\_subtitle\_file = output\_file.rsplit(".", 1)\[0\] + ".srt"

self.log\_message(f"开始转换为SRT格式，目标文件: {srt\_subtitle\_file}")

success = self.convert\_json\_to\_srt(subtitle\_data, srt\_subtitle\_file)

if success:

self.log\_message(f"SRT字幕文件已成功保存: {srt\_subtitle\_file}")

# 优化SRT字幕文件

self.optimize\_srt\_file(srt\_subtitle\_file)

else:

self.log\_message(f"SRT字幕文件转换失败", "ERROR")

except Exception as e:

self.log\_message(f"下载或处理字幕文件失败: {str(e)}", "ERROR")

else:

self.log\_message("同步API没有返回字幕文件，尝试使用异步API生成字幕", "INFO")

# 如果同步API没有返回字幕，尝试使用异步API生成字幕

self.call\_minimax\_async\_api(text, output\_file, mode)

return True

except requests.exceptions.RequestException as e:

self.log\_message(f"API请求失败: {str(e)}", "ERROR")

return False

except Exception as e:

self.log\_message(f"调用MiniMax API失败: {str(e)}", "ERROR")

return False

def call\_minimax\_async\_api(self, text, output\_file, mode="normal"):

"""使用MiniMax异步API生成语音和字幕"""

self.log\_message("正在创建MiniMax异步语音合成任务...")

# 创建临时文本文件

temp\_dir = os.path.join(self.desktop\_path, "Youtube/temp")

os.makedirs(temp\_dir, exist\_ok=True)

# 使用只包含字母和数字的文件名

temp\_txt\_file = os.path.join(temp\_dir, "temptext.txt")

temp\_zip\_file = os.path.join(temp\_dir, "temptext.zip")

# 保存文本到临时文件

with open(temp\_txt\_file, 'w', encoding='utf-8') as f:

f.write(text)

# 创建ZIP文件

import zipfile

with zipfile.ZipFile(temp\_zip\_file, 'w') as zipf:

# 确保ZIP内的文件名也只包含字母和数字

zipf.write(temp\_txt\_file, "temptext.txt")

# 设置API参数

url = f"https://api.minimax.chat/v1/t2a\_async?GroupId={self.minimax\_group\_id}"

headers = {

"Authorization": f"Bearer {self.minimax\_api\_key}"

}

voice\_id = "audiobook\_male\_1" if mode == "normal" else "audiobook\_male\_2"

data = {

'model': 'speech-01',

'voice\_id': voice\_id,

'speed': '1.0',

"vol": '1.0',

"pitch": '0',

"audio\_sample\_rate": '32000',

"bitrate": '128900' # 必须是32900、64900或128900中的一个

}

files = {

'text': open(temp\_zip\_file, 'rb')

}

try:

# 创建异步任务

self.log\_message("提交异步语音合成任务...")

response = requests.post(url, headers=headers, data=data, files=files)

response.raise\_for\_status()

result = response.json()

# 关闭文件

files\['text'\].close()

# 删除临时文件

os.remove(temp\_txt\_file)

os.remove(temp\_zip\_file)

if "base\_resp" not in result or result\["base\_resp"\]\["status\_code"\] != 0:

error\_msg = result.get("base\_resp", {}).get("status\_msg", "未知错误")

self.log\_message(f"异步API请求失败: {error\_msg}", "ERROR")

return False

# 获取任务ID和文件ID

task\_id = result.get("task\_id")

file\_id = result.get("file\_id")

if not task\_id or not file\_id:

self.log\_message("未能获取任务ID或文件ID", "ERROR")

return False

self.log\_message(f"异步任务已创建，任务ID: {task\_id}, 文件ID: {file\_id}")

# 轮询任务状态

max\_retries = 30 # 最多等待30次，每次10秒

for i in range(max\_retries):

status = self.check\_minimax\_async\_task(task\_id)

if status == "Success":

self.log\_message("异步任务处理完成，开始下载结果")

# 下载结果

return self.download\_minimax\_async\_result(file\_id, output\_file)

elif status == "Failed" or status == "Expired":

self.log\_message(f"异步任务处理失败，状态: {status}", "ERROR")

return False

else: # Processing

self.log\_message(f"异步任务处理中，等待中... ({i+1}/{max\_retries})")

time.sleep(10) # 等待10秒再次检查

self.log\_message("异步任务处理超时", "ERROR")

return False

except Exception as e:

self.log\_message(f"异步API请求失败: {str(e)}", "ERROR")

return False

def check\_minimax\_async\_task(self, task\_id):

"""检查MiniMax异步任务状态"""

url = f"https://api.minimax.chat/query/t2a\_async\_query?GroupId={self.minimax\_group\_id}&task\_id={task\_id}"

headers = {

"Authorization": f"Bearer {self.minimax\_api\_key}",

"Content-Type": "application/json"

}

try:

response = requests.get(url, headers=headers)

response.raise\_for\_status()

result = response.json()

if "base\_resp" not in result or result\["base\_resp"\]\["status\_code"\] != 0:

error\_msg = result.get("base\_resp", {}).get("status\_msg", "未知错误")

self.log\_message(f"检查任务状态失败: {error\_msg}", "ERROR")

return "Failed"

status = result.get("status")

return status # Processing, Success, Failed, Expired

except Exception as e:

self.log\_message(f"检查任务状态失败: {str(e)}", "ERROR")

return "Failed"

def download\_minimax\_async\_result(self, file\_id, output\_file):

"""下载MiniMax异步任务结果"""

try:

# 获取文件信息

retrieve\_url = f"https://api.minimax.chat/v1/files/retrieve?GroupId={self.minimax\_group\_id}&file\_id={file\_id}"

headers = {

"Authorization": f"Bearer {self.minimax\_api\_key}",

"Content-Type": "application/json"

}

response = requests.get(retrieve\_url, headers=headers)

response.raise\_for\_status()

data = response.json()

if "base\_resp" not in data or data\["base\_resp"\]\["status\_code"\] != 0:

error\_msg = data.get("base\_resp", {}).get("status\_msg", "未知错误")

self.log\_message(f"获取文件信息失败: {error\_msg}", "ERROR")

return False

# 下载文件内容

download\_url = f"https://api.minimax.chat/v1/files/retrieve\_content?GroupId={self.minimax\_group\_id}&file\_id={file\_id}"

self.log\_message(f"开始下载文件，URL: {download\_url}")

download\_response = requests.get(download\_url, headers=headers)

download\_response.raise\_for\_status()

# 记录响应头信息，用于调试

self.log\_message(f"下载响应头: {dict(download\_response.headers)}")

self.log\_message(f"下载内容大小: {len(download\_response.content)} 字节")

# 检查内容类型

content\_type = download\_response.headers.get('Content-Type', '')

self.log\_message(f"内容类型: {content\_type}")

# 如果是音频文件，直接保存

if 'audio' in content\_type or 'mp3' in content\_type.lower():

# 直接保存为音频文件

with open(output\_file, "wb") as f:

f.write(download\_response.content)

self.log\_message(f"异步API音频文件已直接保存到: {output\_file}")

return True

# 尝试作为ZIP文件处理

try:

import zipfile

from io import BytesIO

zip\_content = BytesIO(download\_response.content)

with zipfile.ZipFile(zip\_content) as zipf:

# 查看ZIP文件内容

file\_list = zipf.namelist()

self.log\_message(f"下载的ZIP文件包含以下文件: {file\_list}")

# 提取音频文件和字幕文件

for file\_name in file\_list:

if file\_name.endswith('.mp3'):

# 保存音频文件

with open(output\_file, 'wb') as f:

f.write(zipf.read(file\_name))

self.log\_message(f"异步API音频文件已保存到: {output\_file}")

elif file\_name.endswith('.json') and ('字幕' in file\_name or 'subtitle' in file\_name.lower()):

# 保存字幕JSON文件

json\_subtitle\_file = output\_file.rsplit(".", 1)\[0\] + ".json"

subtitle\_data = json.loads(zipf.read(file\_name).decode('utf-8'))

with open(json\_subtitle\_file, "w", encoding="utf-8") as f:

json.dump(subtitle\_data, f, ensure\_ascii=False, indent=2)

self.log\_message(f"异步API字幕JSON文件已保存: {json\_subtitle\_file}")

# 转换为SRT格式并保存

srt\_subtitle\_file = output\_file.rsplit(".", 1)\[0\] + ".srt"

self.log\_message(f"开始转换为SRT格式，目标文件: {srt\_subtitle\_file}")

if isinstance(subtitle\_data, list):

success = self.convert\_json\_to\_srt(subtitle\_data, srt\_subtitle\_file)

if success:

self.log\_message(f"异步API SRT字幕文件已成功保存: {srt\_subtitle\_file}")

# 优化SRT字幕文件

self.optimize\_srt\_file(srt\_subtitle\_file)

else:

self.log\_message(f"异步API SRT字幕文件转换失败", "ERROR")

else:

self.log\_message(f"异步API字幕数据格式不是列表，无法转换为SRT", "ERROR")

return True

except zipfile.BadZipFile:

self.log\_message("下载的内容不是有效的ZIP文件，尝试其他处理方式")

# 如果上述方法都失败，直接保存原始文件

self.log\_message("尝试直接保存原始文件")

# 尝试作为JSON处理

try:

json\_data = json.loads(download\_response.content)

self.log\_message(f"内容似乎是JSON数据，尝试处理")

# 保存JSON文件

json\_file = output\_file.rsplit('.', 1)\[0\] + '.json'

with open(json\_file, 'w', encoding='utf-8') as f:

json.dump(json\_data, f, ensure\_ascii=False, indent=2)

self.log\_message(f"JSON数据已保存到: {json\_file}")

# 如果看起来像字幕数据，尝试转换为SRT

if isinstance(json\_data, list) and len(json\_data) > 0:

srt\_file = output\_file.rsplit('.', 1)\[0\] + '.srt'

success = self.convert\_json\_to\_srt(json\_data, srt\_file)

if success:

self.log\_message(f"SRT字幕文件已成功保存: {srt\_file}")

# 优化SRT字幕文件

self.optimize\_srt\_file(srt\_file)

else:

self.log\_message(f"SRT字幕文件转换失败", "ERROR")

return True

except json.JSONDecodeError:

self.log\_message("内容不是JSON数据，直接保存为二进制文件")

# 如果所有尝试都失败，直接保存原始文件

with open(output\_file, 'wb') as f:

f.write(download\_response.content)

self.log\_message(f"原始文件已保存到: {output\_file}")

return True

return True

except Exception as e:

self.log\_message(f"下载异步任务结果失败: {str(e)}", "ERROR")

return False

def generate\_azure\_audio(self, text, output\_file, max\_retries=3):

"""使用Azure TTS生成音频，支持重试和分块处理"""

try:

# 将文本分成较小的块

text\_chunks = self.split\_text\_into\_chunks(text)

total\_chunks = len(text\_chunks)

self.log\_message(f"准备处理 {total\_chunks} 个文本块...")

# 创建临时文件列表

temp\_files = \[\]

subtitles = \[\]

current\_index = 1

total\_duration = 0

# 创建进度条

with tqdm(total=total\_chunks, desc="处理文本块", unit="chunk") as chunk\_pbar:

for chunk\_idx, chunk in enumerate(text\_chunks):

self.log\_message(f"开始处理第 {chunk\_idx + 1} 个文本块，长度: {len(chunk)} 字符")

retry\_count = 0

success = False

while not success and retry\_count < max\_retries:

try:

# 为每个块创建临时文件

temp\_file = f"{output\_file}.part{chunk\_idx}"

temp\_files.append(temp\_file)

synthesizer = speechsdk.SpeechSynthesizer(

speech\_config=self.speech\_config,

audio\_config=speechsdk.audio.AudioOutputConfig(filename=temp\_file)

)

# 存储当前块的字幕信息

current\_segment = \[\]

segment\_start\_time = None

segment\_end\_time = None

first\_word\_of\_segment = True

def handle\_boundary\_event(evt):

nonlocal current\_index, current\_segment, segment\_start\_time, segment\_end\_time

nonlocal first\_word\_of\_segment, total\_duration

if evt.text.strip():

# 计算相对于当前块的时间

current\_time = evt.audio\_offset / 10000000 # 转换为秒

if first\_word\_of\_segment:

segment\_start\_time = total\_duration + current\_time

first\_word\_of\_segment = False

word\_duration = evt.duration.total\_seconds()

segment\_end\_time = total\_duration + current\_time + word\_duration

word = evt.text.strip()

current\_segment.append(word)

# 在句子结束时添加字幕

if any(word.endswith(p) for p in ('.', ',', '。', '，', '!', '?', '！', '？')):

segment\_text = ' '.join(current\_segment)

# 移除末尾的标点符号

segment\_text = segment\_text.rstrip('.,。，!?！？')

if segment\_text: # 确保有内容再添加字幕

subtitles.append(f"{current\_index}\\n"

f"{self.format\_timestamp(segment\_start\_time)} --> {self.format\_timestamp(segment\_end\_time)}\\n"

f"{segment\_text}\\n")

current\_index += 1

current\_segment = \[\]

first\_word\_of\_segment = True

# 连接事件处理器

synthesizer.synthesis\_word\_boundary.connect(handle\_boundary\_event)

# 合成语音

self.log\_message(f"正在合成第 {chunk\_idx + 1} 个文本块...")

result = synthesizer.speak\_text\_async(chunk).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:

self.log\_message(f"第 {chunk\_idx + 1} 个文本块合成成功")

# 更新总时长

audio = AudioSegment.from\_file(temp\_file)

chunk\_duration = audio.duration\_seconds

# 添加一个小的间隔

total\_duration += chunk\_duration + 0.1 # 每个块之间添加0.1秒间隔

success = True

else:

raise Exception("语音合成失败")

except Exception as e:

retry\_count += 1

self.log\_message(f"处理文本块 {chunk\_idx + 1}/{total\_chunks} 失败: {str(e)}，尝试重试 ({retry\_count}/{max\_retries})")

if retry\_count >= max\_retries:

raise Exception(f"处理文本块失败，已达到最大重试次数: {str(e)}")

chunk\_pbar.update(1)

# 合并所有临时文件，添加间隔

self.log\_message("开始合并音频文件...")

combined = AudioSegment.empty()

silence = AudioSegment.silent(duration=100) # 100ms的静音

for temp\_file in temp\_files:

if combined.duration\_seconds > 0:

combined += silence # 在每个块之间添加静音

audio = AudioSegment.from\_file(temp\_file)

combined += audio

# 导出合并后的文件

self.log\_message("保存最终音频文件...")

combined.export(output\_file, format='mp3')

# 保存字幕文件

srt\_file = output\_file.rsplit('.', 1)\[0\] + '.srt'

with open(srt\_file, 'w', encoding='utf-8') as f:

f.write('\\n'.join(subtitles))

# 优化SRT字幕文件

self.optimize\_srt\_file(srt\_file)

# 清理临时文件

self.log\_message("清理临时文件...")

for temp\_file in temp\_files:

try:

os.remove(temp\_file)

except Exception as e:

self.log\_message(f"清理临时文件失败: {str(e)}", "WARNING")

return True

except Exception as e:

self.log\_message(f"Azure TTS错误: {str(e)}", "ERROR")

# 清理临时文件

for temp\_file in temp\_files:

try:

os.remove(temp\_file)

except Exception as e:

self.log\_message(f"清理临时文件失败: {str(e)}", "WARNING")

return False

def split\_text\_into\_chunks(self, text, max\_chars=1000):

"""将文本分成较小的块，以避免连接超时"""

chunks = \[\]

current\_chunk = \[\]

current\_length = 0

# 按句子分割文本

sentences = text.replace('。', '。\\n').replace('！', '！\\n').replace('？', '？\\n').replace('\\n\\n', '\\n').split('\\n')

for sentence in sentences:

sentence = sentence.strip()

if not sentence:

continue

sentence\_length = len(sentence)

# 如果单个句子超过最大长度，按标点符号分割

if sentence\_length > max\_chars:

sub\_sentences = \[\]

temp = ''

for char in sentence:

temp += char

if len(temp) >= max\_chars or char in ('，', '；', '、', ',', ';'):

if temp:

sub\_sentences.append(temp)

temp = ''

if temp:

sub\_sentences.append(temp)

for sub in sub\_sentences:

if current\_length + len(sub) > max\_chars:

chunks.append(''.join(current\_chunk))

current\_chunk = \[sub\]

current\_length = len(sub)

else:

current\_chunk.append(sub)

current\_length += len(sub)

else:

# 如果当前块加上新句子超过最大长度，创建新块

if current\_length + sentence\_length > max\_chars:

chunks.append(''.join(current\_chunk))

current\_chunk = \[sentence\]

current\_length = sentence\_length

else:

current\_chunk.append(sentence)

current\_length += sentence\_length

# 添加最后一个块

if current\_chunk:

chunks.append(''.join(current\_chunk))

return chunks

def merge\_audio\_files(self, audio\_files, output\_file):

"""合并多个音频文件"""

try:

from pydub import AudioSegment

# 读取第一个文件作为基础

combined = AudioSegment.from\_mp3(audio\_files\[0\])

# 添加其他文件

for audio\_file in audio\_files\[1:\]:

audio = AudioSegment.from\_mp3(audio\_file)

combined += audio

# 导出合并后的文件

combined.export(output\_file, format='mp3')

return True

except Exception as e:

self.log\_message(f"合并音频文件失败: {str(e)}", "ERROR")

return False

def process\_single\_file(self, file\_name, whisper\_model="small"):

"""处理单个文件

Args:

file\_name: 要处理的文件名

whisper\_model: Whisper模型大小，可选值: "tiny", "base", "small", "medium", "large"

"""

try:

self.log\_message(f"\\n开始处理文件: {file\_name}")

# 获取文件内容

content = self.read\_docx(file\_name)

if content is None:

self.log\_message(f"文件处理失败: {file\_name}", "ERROR")

return False

# 创建输出文件夹

output\_dir = os.path.join(self.desktop\_path, "Youtube/输出语音")

os.makedirs(output\_dir, exist\_ok=True)

# 设置输出文件路径

output\_file = os.path.join(output\_dir, f"{file\_name}.mp3")

# 根据选择的模式生成音频

mode = self.file\_modes.get(file\_name, "normal")

if mode == "azure":

success = self.generate\_azure\_audio(content, output\_file)

else:

success = self.call\_minimax\_api(content, output\_file, mode, generate\_srt=False) # 不生成SRT

if success:

self.log\_message(f"文件处理成功: {file\_name}")

# 直接使用Whisper生成字幕

self.log\_message(f"正在使用Whisper({whisper\_model}模型)进行语音识别和字幕生成...")

whisper\_srt\_file = self.generate\_whisper\_subtitles(output\_file, model\_size=whisper\_model)

if whisper\_srt\_file and os.path.exists(whisper\_srt\_file):

# 使用原始Word文档内容校正Whisper识别的字幕

self.log\_message("正在使用原始Word文档内容校正Whisper识别的字幕...")

corrected\_srt\_file = output\_file.rsplit('.', 1)\[0\] + '.srt' # 最终SRT文件

self.correct\_whisper\_with\_word\_content(whisper\_srt\_file, content, corrected\_srt\_file)

self.log\_message(f"生成校正后的字幕文件: {corrected\_srt\_file}")

# 清理中间文件

try:

if os.path.exists(whisper\_srt\_file):

os.remove(whisper\_srt\_file)

self.log\_message(f"已清理中间文件: {whisper\_srt\_file}")

except Exception as e:

self.log\_message(f"清理中间文件失败: {str(e)}", "WARNING")

return True

else:

self.log\_message(f"文件处理失败: {file\_name}", "ERROR")

return False

except Exception as e:

self.log\_message(f"处理文件时出错: {str(e)}", "ERROR")

return False

def process\_files(self):

"""处理所有选中的文件"""

self.log\_message("\\n开始处理选中的文件...")

# 获取所有需要处理的文件

files\_to\_process = \[f for f in self.file\_modes.keys()\]

total\_files = len(files\_to\_process)

# 使用tqdm创建总体进度条

with tqdm(total=total\_files, desc="总体进度", unit="file") as pbar:

for i, file\_name in enumerate(files\_to\_process, 1):

self.log\_message(f"\\n处理文件 ({i}/{total\_files}): {file\_name}")

success = self.process\_single\_file(file\_name, whisper\_model=self.whisper\_model)

pbar.update(1)

if not success:

self.log\_message(f"文件处理失败: {file\_name}", "ERROR")

self.log\_message("\\n所有文件处理完成!")

def get\_docx\_files(self):

"""获取改写文件夹中的docx文件"""

try:

if not os.path.exists(self.rewrite\_path):

self.log\_message("改写文件夹不存在", "ERROR")

return \[\]

# 获取所有文件

files = \[f for f in os.listdir(self.rewrite\_path) \
\
if os.path.isfile(os.path.join(self.rewrite\_path, f)) and \
\
f.endswith(('.docx', '.txt')) and \
\
not f.startswith('~$')\] # 排除临时文件

# 存储文件名和原始文件名的映射

self.file\_mapping = {}

display\_files = \[\]

for file in sorted(files):

# 去掉扩展名用于显示

display\_name = os.path.splitext(file)\[0\]

if display\_name not in self.file\_mapping:

display\_files.append(display\_name)

self.file\_mapping\[display\_name\] = file

self.log\_message(f"改写文件夹路径: {self.rewrite\_path}")

self.log\_message(f"改写文件夹文件总数: {len(files)}")

return display\_files

except Exception as e:

self.log\_message(f"获取文件列表失败: {str(e)}", "ERROR")

return \[\]

def combine\_whisper\_timestamps\_with\_original\_text(self, whisper\_srt\_file, original\_srt\_file, output\_srt\_file=None):

"""结合Whisper的时间戳和原始字幕的文本内容，使用GPT-4o-mini修正文本

保持Whisper的时间戳不变，使用GPT-4o-mini对比原始文本和Whisper文本，修正错别字

Args:

whisper\_srt\_file: Whisper生成的SRT文件路径（包含准确的时间戳）

original\_srt\_file: 原始SRT文件路径（包含准确的文本内容）

output\_srt\_file: 输出SRT文件路径，如果为None，则默认为original\_srt\_file + '\_perfect.srt'

"""

try:

self.log\_message(f"开始使用GPT-4o-mini修正Whisper字幕文本...")

# 读取Whisper生成的SRT文件

with open(whisper\_srt\_file, 'r', encoding='utf-8') as f:

whisper\_content = f.read()

# 读取原始SRT文件

with open(original\_srt\_file, 'r', encoding='utf-8') as f:

original\_content = f.read()

# 解析SRT内容

whisper\_blocks = whisper\_content.strip().split('\\n\\n')

original\_blocks = original\_content.strip().split('\\n\\n')

# 提取Whisper字幕的时间戳和文本

whisper\_segments = \[\]

for block in whisper\_blocks:

lines = block.strip().split('\\n')

if len(lines) < 3:

continue

# 提取索引、时间轴和文本

index = lines\[0\]

time\_line = lines\[1\]

text = '\\n'.join(lines\[2:\])

whisper\_segments.append({

'index': index,

'time\_line': time\_line,

'text': text

})

# 提取原始字幕的文本内容

original\_text = ""

for block in original\_blocks:

lines = block.strip().split('\\n')

if len(lines) < 3:

continue

# 提取文本

text = '\\n'.join(lines\[2:\])

original\_text += text + " "

# 准备GPT-4o-mini的输入

whisper\_texts = \[segment\['text'\] for segment in whisper\_segments\]

# 调用GPT-4o-mini进行文本修正

corrected\_texts = self.correct\_texts\_with\_gpt(whisper\_texts, original\_text)

# 创建新的字幕块

new\_blocks = \[\]

for i, segment in enumerate(whisper\_segments):

if i < len(corrected\_texts):

# 使用修正后的文本

corrected\_text = corrected\_texts\[i\]

new\_blocks.append(f"{segment\['index'\]}\\n{segment\['time\_line'\]}\\n{corrected\_text}")

else:

# 如果没有对应的修正文本，使用原始Whisper文本

new\_blocks.append(f"{segment\['index'\]}\\n{segment\['time\_line'\]}\\n{segment\['text'\]}")

# 设置输出文件路径

if output\_srt\_file is None:

output\_srt\_file = original\_srt\_file.rsplit('.', 1)\[0\] + '\_perfect.srt'

# 写入结合后的SRT文件

with open(output\_srt\_file, 'w', encoding='utf-8') as f:

f.write('\\n\\n'.join(new\_blocks))

self.log\_message(f"GPT-4o-mini修正完成，保存到: {output\_srt\_file}")

return True

except Exception as e:

self.log\_message(f"使用GPT-4o-mini修正字幕失败: {str(e)}", "ERROR")

return False

def correct\_texts\_with\_gpt(self, whisper\_texts, original\_text):

"""使用GPT-4o-mini修正Whisper文本中的错别字，并确保句子边界正确

Args:

whisper\_texts: Whisper识别的文本列表

original\_text: 原始文本内容

Returns:

修正后的文本列表

"""

try:

from openai import OpenAI

self.log\_message("正在使用GPT-4o-mini修正文本和句子边界...")

# 初始化OpenAI客户端

client = OpenAI(

base\_url="",

api\_key=""

)

# 构建提示词，强调句子边界的重要性

prompt = f"""

你是一个专业的字幕修正助手。我需要你帮助修正语音识别生成的字幕文本中可能存在的错别字，并确保句子边界正确。

原始准确文本（来自Word文档，绝对正确）:

"{original\_text}"

Whisper识别的文本（可能包含错别字和句子边界问题）:

"""

# 添加Whisper文本，并标明每句的编号

for i, text in enumerate(whisper\_texts):

prompt += f"\\n\[{i+1}\] {text}"

prompt += """

请执行以下任务：

1\. 逐句修正Whisper识别的文本，使其与原始准确文本的意思一致

2\. 确保每个句子的边界正确，避免出现"串行"问题（即一句话的内容错误地分到下一句）

3\. 保持Whisper的断句数量，但修正每句的内容，使其成为完整且独立的句子

4\. 如果发现某句话内容应该属于另一句，请适当调整

你的输出应该只包含修正后的文本，每句一行，使用与输入相同的编号格式：

\[1\] 修正后的第一句

\[2\] 修正后的第二句

...

保持原始的标点符号和格式，只修正错别字和句子边界问题。

"""

# 调用GPT-4o-mini

response = client.chat.completions.create(

model="gpt-4o-mini-2024-07-18",

messages=\[\
\
{"role": "system", "content": "你是一个专业的字幕修正助手，擅长修正语音识别文本中的错别字和句子边界问题。"},\
\
{"role": "user", "content": prompt}\
\
\],

temperature=0.2, # 使用较低的温度以获得更确定的结果

max\_tokens=4000

)

# 获取响应文本

corrected\_text = response.choices\[0\].message.content.strip()

# 分割为单独的行

corrected\_lines = corrected\_text.split('\\n')

# 过滤掉空行和可能的额外信息

corrected\_lines = \[line.strip() for line in corrected\_lines if line.strip()\]

# 提取编号和文本

import re

corrected\_texts = \[\]

for line in corrected\_lines:

# 匹配 \[数字\] 文本 格式

match = re.match(r'^\\\[(\\d+)\\\]\\s\*(.\*)', line)

if match:

index = int(match.group(1)) - 1

text = match.group(2).strip()

# 确保索引在范围内

while len(corrected\_texts) <= index:

corrected\_texts.append("")

corrected\_texts\[index\] = text

else:

# 如果没有编号格式，直接添加到结果中

corrected\_texts.append(line)

self.log\_message(f"GPT-4o-mini成功修正了 {len(corrected\_texts)} 行文本，并确保句子边界正确")

return corrected\_texts

except Exception as e:

self.log\_message(f"GPT-4o-mini修正文本失败: {str(e)}", "ERROR")

return whisper\_texts # 如果失败，返回原始文本

def correct\_whisper\_with\_word\_content(self, whisper\_srt\_file, original\_content, output\_srt\_file=None):

"""使用Word文档原始内容校正Whisper识别的字幕

保持Whisper的时间戳不变，使用GPT-4o-mini对比原始文本和Whisper文本，修正错别字和句子边界问题

Args:

whisper\_srt\_file: Whisper生成的SRT文件路径（包含准确的时间戳）

original\_content: Word文档的原始内容（包含准确的文本）

output\_srt\_file: 输出SRT文件路径，如果为None，则默认为whisper\_srt\_file + '\_corrected.srt'

"""

try:

self.log\_message(f"开始使用GPT-4o-mini校正Whisper字幕文本和句子边界...")

# 读取Whisper生成的SRT文件

with open(whisper\_srt\_file, 'r', encoding='utf-8') as f:

whisper\_content = f.read()

# 解析SRT内容

whisper\_blocks = whisper\_content.strip().split('\\n\\n')

# 提取Whisper字幕的时间戳和文本

whisper\_segments = \[\]

for block in whisper\_blocks:

lines = block.strip().split('\\n')

if len(lines) < 3:

continue

# 提取索引、时间轴和文本

index = lines\[0\]

time\_line = lines\[1\]

text = '\\n'.join(lines\[2:\])

whisper\_segments.append({

'index': index,

'time\_line': time\_line,

'text': text

})

# 提取原始Word文档的文本内容

original\_text = original\_content.strip()

# 准备GPT-4o-mini的输入

whisper\_texts = \[segment\['text'\] for segment in whisper\_segments\]

# 调用GPT-4o-mini进行文本修正和句子边界校正

corrected\_texts = self.correct\_texts\_with\_gpt(whisper\_texts, original\_text)

# 创建新的字幕块

new\_blocks = \[\]

for i, segment in enumerate(whisper\_segments):

if i < len(corrected\_texts) and corrected\_texts\[i\]:

# 使用修正后的文本

corrected\_text = corrected\_texts\[i\]

new\_blocks.append(f"{segment\['index'\]}\\n{segment\['time\_line'\]}\\n{corrected\_text}")

else:

# 如果没有对应的修正文本，使用原始Whisper文本

new\_blocks.append(f"{segment\['index'\]}\\n{segment\['time\_line'\]}\\n{segment\['text'\]}")

# 设置输出文件路径

if output\_srt\_file is None:

output\_srt\_file = whisper\_srt\_file.rsplit('.', 1)\[0\] + '\_corrected.srt'

# 写入校正后的SRT文件

with open(output\_srt\_file, 'w', encoding='utf-8') as f:

f.write('\\n\\n'.join(new\_blocks))

self.log\_message(f"GPT-4o-mini校正完成，保存到: {output\_srt\_file}")

return True

except Exception as e:

self.log\_message(f"使用GPT-4o-mini校正字幕失败: {str(e)}", "ERROR")

return False

def align\_subtitles\_with\_audio(self, audio\_file, srt\_file):

"""使用语音识别技术将字幕与音频精确对齐"""

try:

self.log\_message(f"开始将字幕与音频对齐: {srt\_file}")

# 导入必要的库

import speech\_recognition as sr

from pydub import AudioSegment

import jieba

import re

# 读取原始SRT文件

with open(srt\_file, 'r', encoding='utf-8') as f:

content = f.read()

# 解析SRT内容，获取所有文本

srt\_blocks = content.strip().split('\\n\\n')

all\_text = ""

for block in srt\_blocks:

lines = block.strip().split('\\n')

if len(lines) < 3:

continue

# 提取文本

text = '\\n'.join(lines\[2:\])

all\_text += text + " "

# 使用jieba分词

words = list(jieba.cut(all\_text))

# 加载音频文件

audio = AudioSegment.from\_file(audio\_file)

# 将音频转换为WAV格式（语音识别需要）

temp\_wav = audio\_file.rsplit('.', 1)\[0\] + '\_temp.wav'

audio.export(temp\_wav, format="wav")

# 初始化语音识别器

r = sr.Recognizer()

# 创建新的字幕块

new\_blocks = \[\]

new\_index = 1

# 分析音频

with sr.AudioFile(temp\_wav) as source:

# 调整识别器参数以适应音频

r.adjust\_for\_ambient\_noise(source)

# 设置音频段的长度（秒）

segment\_length = 5 # 5秒一段

total\_duration = len(audio) / 1000 # 总时长（秒）

for i in range(0, int(total\_duration), segment\_length):

# 设置当前段的开始和结束时间

start\_time = i

end\_time = min(i + segment\_length, total\_duration)

# 获取当前音频段

audio\_segment = r.record(source, duration=end\_time-start\_time)

try:

# 使用Google语音识别API（需要联网）

segment\_text = r.recognize\_google(audio\_segment, language="zh-CN")

# 查找原始字幕中最匹配的文本

best\_match = self.find\_best\_match(segment\_text, all\_text)

if best\_match:

# 创建新的字幕块

start\_time\_str = self.format\_timestamp(start\_time)

end\_time\_str = self.format\_timestamp(end\_time)

# 对匹配的文本进行分割，确保每行不超过13个字符

split\_texts = self.split\_subtitle\_text(best\_match)

# 计算每个分割文本的时长

sub\_duration = (end\_time - start\_time) \* 1000 / len(split\_texts)

for j, sub\_text in enumerate(split\_texts):

sub\_start = start\_time \* 1000 + j \* sub\_duration

sub\_end = sub\_start + sub\_duration

sub\_start\_str = self.ms\_to\_srt\_time(sub\_start)

sub\_end\_str = self.ms\_to\_srt\_time(sub\_end)

new\_blocks.append(f"{new\_index}\\n{sub\_start\_str} --> {sub\_end\_str}\\n{sub\_text}")

new\_index += 1

except sr.UnknownValueError:

self.log\_message(f"无法识别音频段 {start\_time}-{end\_time} 秒", "WARNING")

except sr.RequestError as e:

self.log\_message(f"无法请求Google语音识别服务: {e}", "ERROR")

break

# 删除临时WAV文件

try:

os.remove(temp\_wav)

except:

pass

# 如果没有生成新的字幕块，返回失败

if not new\_blocks:

self.log\_message("未能生成任何对齐的字幕", "ERROR")

return False

# 写入对齐后的SRT文件

aligned\_srt\_file = srt\_file.rsplit('.', 1)\[0\] + '\_aligned.srt'

with open(aligned\_srt\_file, 'w', encoding='utf-8') as f:

f.write('\\n\\n'.join(new\_blocks))

self.log\_message(f"字幕与音频对齐完成，保存到: {aligned\_srt\_file}")

return True

except Exception as e:

self.log\_message(f"字幕与音频对齐失败: {str(e)}", "ERROR")

return False

def align\_subtitles\_with\_whisper(self, audio\_file, srt\_file):

"""使用Whisper将字幕与音频精确对齐"""

try:

self.log\_message(f"开始使用Whisper将字幕与音频对齐: {srt\_file}")

# 导入必要的库

import whisper

import numpy as np

import tempfile

from pydub import AudioSegment

# 读取原始SRT文件

with open(srt\_file, 'r', encoding='utf-8') as f:

content = f.read()

# 解析SRT内容，获取所有文本

srt\_blocks = content.strip().split('\\n\\n')

all\_text = ""

for block in srt\_blocks:

lines = block.strip().split('\\n')

if len(lines) < 3:

continue

# 提取文本

text = '\\n'.join(lines\[2:\])

all\_text += text + " "

# 加载Whisper模型（使用较小的模型以提高速度）

self.log\_message("正在加载Whisper模型...")

model = whisper.load\_model("tiny") # 可选: "tiny", "base", "small", "medium", "large"

# 将音频转换为WAV格式（如果不是WAV）

if not audio\_file.lower().endswith('.wav'):

self.log\_message("转换音频为WAV格式...")

audio = AudioSegment.from\_file(audio\_file)

temp\_wav = audio\_file.rsplit('.', 1)\[0\] + '\_temp.wav'

audio.export(temp\_wav, format="wav")

audio\_path = temp\_wav

else:

audio\_path = audio\_file

# 使用Whisper进行语音识别

self.log\_message("开始进行语音识别...")

result = model.transcribe(audio\_path, language="zh")

# 创建新的字幕块

new\_blocks = \[\]

# 处理识别结果中的每个段落

for i, segment in enumerate(result\["segments"\]):

start\_time = segment\["start"\]

end\_time = segment\["end"\]

text = segment\["text"\].strip()

# 如果文本为空，跳过

if not text:

continue

# 将时间转换为SRT格式

start\_time\_str = self.ms\_to\_srt\_time(start\_time \* 1000)

end\_time\_str = self.ms\_to\_srt\_time(end\_time \* 1000)

# 对文本进行分割，确保每行不超过13个字符

split\_texts = self.split\_subtitle\_text(text)

# 计算每个分割文本的时长

segment\_duration = (end\_time - start\_time) \* 1000

sub\_duration = segment\_duration / len(split\_texts)

# 为每个分割文本创建字幕块

for j, sub\_text in enumerate(split\_texts):

sub\_start = start\_time \* 1000 + j \* sub\_duration

sub\_end = sub\_start + sub\_duration

sub\_start\_str = self.ms\_to\_srt\_time(sub\_start)

sub\_end\_str = self.ms\_to\_srt\_time(sub\_end)

new\_blocks.append(f"{len(new\_blocks) + 1}\\n{sub\_start\_str} --> {sub\_end\_str}\\n{sub\_text}")

# 删除临时WAV文件

if not audio\_file.lower().endswith('.wav') and os.path.exists(temp\_wav):

try:

os.remove(temp\_wav)

except:

pass

# 如果没有生成新的字幕块，返回失败

if not new\_blocks:

self.log\_message("未能生成任何对齐的字幕", "ERROR")

return False

# 写入对齐后的SRT文件

aligned\_srt\_file = srt\_file.rsplit('.', 1)\[0\] + '\_whisper.srt'

with open(aligned\_srt\_file, 'w', encoding='utf-8') as f:

f.write('\\n\\n'.join(new\_blocks))

self.log\_message(f"字幕与音频对齐完成，保存到: {aligned\_srt\_file}")

return aligned\_srt\_file

except Exception as e:

self.log\_message(f"使用Whisper对齐字幕失败: {str(e)}", "ERROR")

return False

def find\_best\_match(self, recognized\_text, original\_text):

"""查找原始文本中与识别文本最匹配的部分"""

import difflib

# 使用difflib查找最佳匹配

matcher = difflib.SequenceMatcher(None, recognized\_text, original\_text)

match = matcher.find\_longest\_match(0, len(recognized\_text), 0, len(original\_text))

if match.size > 5: # 至少匹配5个字符

return original\_text\[match.b:match.b + match.size\]

return None

def generate\_whisper\_subtitles(self, audio\_file, model\_size="small"):

"""使用Whisper直接从音频生成字幕文件

Args:

audio\_file: 音频文件路径

model\_size: Whisper模型大小，可选值: "tiny", "base", "small", "medium", "large"

默认为"small"，平衡了速度和准确度

Returns:

生成的SRT文件路径，如果失败则返回False

"""

try:

self.log\_message(f"开始使用Whisper({model\_size}模型)从音频生成字幕: {audio\_file}")

# 导入必要的库

import whisper

import numpy as np

import tempfile

from pydub import AudioSegment

# 验证模型大小参数

valid\_models = \["tiny", "base", "small", "medium", "large"\]

if model\_size not in valid\_models:

self.log\_message(f"无效的模型大小: {model\_size}，使用默认的'small'模型", "WARNING")

model\_size = "small"

# 加载Whisper模型

self.log\_message(f"正在加载Whisper {model\_size}模型...")

model = whisper.load\_model(model\_size)

# 将音频转换为WAV格式（如果不是WAV）

if not audio\_file.lower().endswith('.wav'):

self.log\_message("转换音频为WAV格式...")

audio = AudioSegment.from\_file(audio\_file)

temp\_wav = audio\_file.rsplit('.', 1)\[0\] + '\_temp.wav'

audio.export(temp\_wav, format="wav")

audio\_path = temp\_wav

else:

audio\_path = audio\_file

# 使用Whisper进行语音识别，设置更多参数以提高准确性

self.log\_message("开始进行语音识别...")

result = model.transcribe(

audio\_path,

language="zh",

word\_timestamps=True, # 获取更精确的单词时间戳

condition\_on\_previous\_text=True, # 考虑前文上下文

fp16=False # 使用更精确的浮点计算

)

# 创建新的字幕块

new\_blocks = \[\]

# 处理识别结果中的每个段落

for i, segment in enumerate(result\["segments"\]):

start\_time = segment\["start"\]

end\_time = segment\["end"\]

text = segment\["text"\].strip()

# 如果文本为空，跳过

if not text:

continue

# 将时间转换为SRT格式

start\_time\_str = self.ms\_to\_srt\_time(start\_time \* 1000)

end\_time\_str = self.ms\_to\_srt\_time(end\_time \* 1000)

# 对文本进行分割，确保每行不超过13个字符

split\_texts = self.split\_subtitle\_text(text)

# 计算每个分割文本的时长

segment\_duration = (end\_time - start\_time) \* 1000

sub\_duration = segment\_duration / len(split\_texts)

# 为每个分割文本创建字幕块

for j, sub\_text in enumerate(split\_texts):

sub\_start = start\_time \* 1000 + j \* sub\_duration

sub\_end = sub\_start + sub\_duration

sub\_start\_str = self.ms\_to\_srt\_time(sub\_start)

sub\_end\_str = self.ms\_to\_srt\_time(sub\_end)

new\_blocks.append(f"{len(new\_blocks) + 1}\\n{sub\_start\_str} --> {sub\_end\_str}\\n{sub\_text}")

# 删除临时WAV文件

if not audio\_file.lower().endswith('.wav') and os.path.exists(temp\_wav):

try:

os.remove(temp\_wav)

except:

pass

# 如果没有生成新的字幕块，返回失败

if not new\_blocks:

self.log\_message("未能生成任何字幕", "ERROR")

return False

# 写入生成的SRT文件

whisper\_srt\_file = audio\_file.rsplit('.', 1)\[0\] + '\_whisper\_temp.srt'

with open(whisper\_srt\_file, 'w', encoding='utf-8') as f:

f.write('\\n\\n'.join(new\_blocks))

self.log\_message(f"Whisper字幕生成完成，保存到: {whisper\_srt\_file}")

return whisper\_srt\_file

except Exception as e:

self.log\_message(f"使用Whisper生成字幕失败: {str(e)}", "ERROR")

return False

def main():

generator = TTSGenerator()

if \_\_name\_\_ == "\_\_main\_\_":

main()
