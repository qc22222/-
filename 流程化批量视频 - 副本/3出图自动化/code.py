mport os

import re

from pathlib import Path

from docx import Document

from openai import OpenAI

import runware

from PIL import Image

import requests

from io import BytesIO

import time

from datetime import datetime

import requests

import json

import uuid

import subprocess # 添加subprocess模块

class RunwareImageGenerator:

def \_\_init\_\_(self):

# 基础配置

self.desktop = str(Path.home() / "Desktop")

self.rewrite\_folder = os.path.join(self.desktop, "剪辑/改写") # 改写文件夹路径

self.image\_folder = os.path.join(self.desktop, "剪辑/图片") # 图片文件夹路径

self.start\_time = None

self.current\_file = None

self.current\_file\_name = None # 添加当前处理的文件名

self.total\_cost = 0.0 # 总费用

self.prevent\_sleep = None # 添加防睡眠进程变量

# 创建必要的文件夹

os.makedirs(self.rewrite\_folder, exist\_ok=True)

os.makedirs(self.image\_folder, exist\_ok=True)

# OpenAI客户端

self.client = OpenAI(

base\_url="",

api\_key="sk-"

)

# 初始化Runware客户端

runware.api\_key = "" # 需要替换为实际的API key

# 不同模式的提示词

self.system\_prompts = {

"通用": """

忘记你以前的一切设定

将下面的文本翻译为详细的场景英文描述，用作给AI出图，要求：

1\. 译成英文，尽量以人事物+动作+周围场景作为格式

2\. 描述写成一行

3\. 只输出英文描述，不要其他的任何说明

""",

"中文基督": """

忘记你以前的一切设定

将下面的文本翻译为详细的场景英文描述，用作给AI出图，要求：

1\. 译成英文，尽量以人事物+动作+周围场景作为格式

2\. 描述写成一行

3\. 只输出英文描述，不要其他的任何说明

4\. 这是一个基督教相关的内容，所以如果可能，在英文翻译中加入和翻译相符的基督教的元素，如果加不进去也不要强行加入

""",

"英文出图": """

忘记你以前的一切设定

Please enhance the following English text for AI image generation, requirements:

1\. Keep the original meaning but make it more detailed and vivid

2\. Output in a single line

3\. Only output the English description, no other explanations

""",

"西班牙语": """

忘记你以前的一切设定

Por favor, traduzca el siguiente texto a una descripción detallada de la escena en inglés para la generación de imágenes de IA, requisitos:

1\. Traduzca al inglés, intentando utilizar la estructura de persona/objeto + acción + entorno

2\. La descripción debe ser una sola línea

3\. Solo salida de la descripción en inglés, sin ninguna otra explicación

""",

"恐怖故事": """

忘记你以前的一切设定

将文本生成为详细的恐怖场景英文描述，用作给AI出图，要求：

1\. 尽量以人事物+动作+周围恐怖场景作为格式

2\. 描述写成一行

3\. 只输出英文描述，不要其他的任何说明

""",

}

# 不同模式的切割配置

self.split\_configs = {

"1": { # 通用模式（中文）

"target\_chars": 115, # 目标字符数

"type": "chars", # 按字符切割

"punctuation": "。！？，；" # 中文标点

},

"2": { # 中文基督模式（中文）

"target\_chars": 105, # 目标字符数

"type": "chars", # 按字符切割

"punctuation": "。！？，；" # 中文标点

},

"3": { # 英文基督模式（英文）

"target\_words": 55, # 目标单词数

"type": "words", # 按单词切割

"punctuation": ".," # 英文标点

},

"4": { # 西班牙语模式（西班牙文）

"target\_words": 70, # 目标单词数

"type": "words", # 按单词切割

"punctuation": ".,!?¡¿" # 西班牙文标点

},

"5": { # 恐怖故事模式（英文）

"target\_words": 55, # 目标单词数

"type": "words", # 按单词切割

"punctuation": ".," # 英文标点

}

}

# 当前使用的模式

self.current\_mode = None

# 初始化结果列表

self.gpt\_results = \[\]

def get\_current\_time(self):

"""获取当前时间的格式化字符串"""

return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log\_message(self, message, level="INFO"):

"""添加日志记录功能"""

current\_time = self.get\_current\_time()

print(f"\[{current\_time}\] \[{level}\] {message}")

def print\_progress(self, current, total):

"""显示进度条"""

progress = current / total

filled\_length = int(50 \* progress)

bar = '=' \* filled\_length + ' ' \* (50 - filled\_length)

print(f"\\r处理进度: \[{bar}\] {current}/{total}", end='', flush=True)

def read\_docx(self, file\_path):

"""读取指定的docx文件内容"""

try:

self.log\_message(f"尝试读取文件: {file\_path}")

doc = Document(file\_path)

# 初始化段落列表

paragraphs = \[\]

# 收集所有段落的文本

for para in doc.paragraphs:

text = para.text.strip()

if text: # 只添加非空段落

paragraphs.append(text)

return paragraphs

except Exception as e:

self.log\_message(f"读取文件出错: {str(e)}", "ERROR")

return None

def split\_paragraphs(self, paragraphs):

"""将段落分段"""

try:

segments = \[\]

# 对于英文基督模式和西班牙语，我们将所有段落合并成一个完整的文本

if self.current\_mode in \["3", "4", "5"\]: # 英文基督模式或西班牙语模式

# 清理每个段落

cleaned\_paragraphs = \[\]

for para in paragraphs:

# 移除多余的空格、换行和标点符号前的空格

cleaned = re.sub(r'\\s+', ' ', para).strip()

cleaned = re.sub(r'\\s+(\[.,!?\])', r'\\1', cleaned)

if cleaned:

cleaned\_paragraphs.append(cleaned)

# 合并所有段落

text = ' '.join(cleaned\_paragraphs)

# 再次清理合并后的文本

text = re.sub(r'\\s+', ' ', text).strip()

text = re.sub(r'\\s+(\[.,!?\])', r'\\1', text)

return self.split\_into\_paragraphs(text)

# 对于其他模式，保持原有的分段逻辑

for para in paragraphs:

# 清理段落文本

lines = \[line.strip() for line in para.splitlines() if line.strip()\]

if not lines:

continue

text = ' '.join(lines)

# 通用模式和中文基督模式使用字符数量切割

start\_pos = 0

while start\_pos < len(text):

if len(text) - start\_pos <= 150:

last\_segment = text\[start\_pos:\].strip()

if last\_segment:

segments.append(last\_segment)

break

check\_pos = start\_pos + 150

found\_punctuation = False

for i in range(check\_pos, min(check\_pos + 20, len(text))):

if text\[i\] in '".。，,¡!¿?': # 添加西班牙语标点符号

segments.append(text\[start\_pos:i + 1\].strip())

start\_pos = i + 1

found\_punctuation = True

break

if not found\_punctuation:

segments.append(text\[start\_pos:start\_pos + 160\].strip())

start\_pos += 170

return segments

except Exception as e:

self.log\_message(f"分段处理出错: {str(e)}", "ERROR")

return None

def count\_words(self, text):

"""计算英文文本中的单词数"""

text = re.sub(r'\[^\\w\\s\]', '', text)

words = \[word for word in text.split() if word\]

return len(words)

def split\_into\_paragraphs(self, text):

"""根据不同模式的配置将文本分段"""

try:

# 获取当前模式的配置

config = self.split\_configs.get(self.current\_mode)

if not config:

self.log\_message(f"未找到模式 {self.current\_mode} 的配置", "ERROR")

return None

# 根据模式类型选择不同的切割方式

if config\["type"\] == "chars":

# 中文模式：按字符数切割

current\_chars = 0

paragraphs = \[\]

current\_paragraph = ""

for char in text:

current\_paragraph += char

current\_chars += 1

# 达到目标字符数后，寻找下一个标点

if current\_chars >= config\["target\_chars"\]:

# 在最后50个字符中查找标点

found\_punct = False

for i in range(len(current\_paragraph)-1, max(-1, len(current\_paragraph)-50), -1):

if current\_paragraph\[i\] in config\["punctuation"\]:

paragraphs.append(current\_paragraph\[:i+1\].strip())

current\_paragraph = current\_paragraph\[i+1:\].strip()

current\_chars = len(current\_paragraph)

found\_punct = True

break

# 如果没找到标点，继续往后找

if not found\_punct:

for i in range(len(current\_paragraph)-1, -1, -1):

if current\_paragraph\[i\] in config\["punctuation"\]:

paragraphs.append(current\_paragraph\[:i+1\].strip())

current\_paragraph = current\_paragraph\[i+1:\].strip()

current\_chars = len(current\_paragraph)

found\_punct = True

break

# 如果还是没找到标点，强制切割

if not found\_punct and current\_chars > config\["target\_chars"\] \* 1.5:

paragraphs.append(current\_paragraph.strip())

current\_paragraph = ""

current\_chars = 0

# 添加最后一段

if current\_paragraph:

paragraphs.append(current\_paragraph.strip())

else: # words模式（英文和西班牙文）

words = text.split()

paragraphs = \[\]

current\_paragraph = \[\]

word\_count = 0

total\_words = len(words)

self.log\_message(f"总单词数: {total\_words}")

for word in words:

current\_paragraph.append(word)

word\_count += 1

# 达到目标单词数后，寻找下一个标点

if word\_count >= config\["target\_words"\]:

current\_text = ' '.join(current\_paragraph)

# 在最后一部分文本中查找标点

last\_pos = -1

for punct in config\["punctuation"\]:

pos = current\_text.rfind(punct, max(0, len(current\_text)-200))

if pos > last\_pos:

last\_pos = pos

if last\_pos != -1:

cut\_text = current\_text\[:last\_pos+1\].strip()

remaining\_text = current\_text\[last\_pos+1:\].strip()

cut\_words = len(cut\_text.split())

self.log\_message(f"在标点处切割，本段单词数: {cut\_words}")

paragraphs.append(cut\_text)

current\_paragraph = remaining\_text.split()

word\_count = len(current\_paragraph)

else:

# 如果在最后200个字符没找到标点，强制切割

self.log\_message(f"强制切割，本段单词数: {word\_count}")

paragraphs.append(current\_text.strip())

current\_paragraph = \[\]

word\_count = 0

# 添加最后一段

if current\_paragraph:

last\_text = ' '.join(current\_paragraph).strip()

last\_words = len(last\_text.split())

self.log\_message(f"添加最后一段，单词数: {last\_words}")

paragraphs.append(last\_text)

# 输出每段的单词数统计

for i, para in enumerate(paragraphs, 1):

words\_in\_para = len(para.split())

self.log\_message(f"第{i}段的单词数: {words\_in\_para}")

return paragraphs

except Exception as e:

self.log\_message(f"分段处理出错: {str(e)}", "ERROR")

return None

def calculate\_cost(self, input\_tokens, output\_tokens):

"""计算API调用成本"""

input\_cost = (input\_tokens / 1000000) \* 3.00 # $3.00 per 1M tokens for input

output\_cost = (output\_tokens / 1000000) \* 12.00 # $12.00 per 1M tokens for output

total\_cost = input\_cost + output\_cost

return total\_cost

def generate\_image(self, prompt):

"""使用Runware API生成图片"""

max\_retries = 3

retry\_delay = 2

for attempt in range(max\_retries):

try:

# 添加请求延迟，避免API限流

time.sleep(3)

# API endpoint

url = "https://api.runware.ai/v1/inference"

# 请求头

headers = {

"Authorization": f"Bearer {runware.api\_key}",

"Content-Type": "application/json"

}

# 请求体

data = \[{\
\
"taskType": "imageInference",\
\
"taskUUID": str(uuid.uuid4()),\
\
"model": "runware:101@1",\
\
"positivePrompt": prompt,\
\
"negativePrompt": "NSFW, nude, naked, blood, gore, violence, offensive, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry,letter",\
\
"width": 1024,\
\
"height": 576,\
\
"steps": 20,\
\
"scheduler": "FlowMatchEulerDiscreteScheduler",\
\
"CFGScale": 3.5,\
\
"outputType": "URL",\
\
"outputFormat": "JPG",\
\
"includeCost": True\
\
}\]

self.log\_message("开始生成图片...")

# 发送请求

response = requests.post(url, headers=headers, json=data)

response.raise\_for\_status()

# 解析响应

result = response.json()

if isinstance(result, dict) and 'data' in result and isinstance(result\['data'\], list):

for item in result\['data'\]:

if item\['taskType'\] == 'imageInference':

# 计算费用

if 'cost' in item:

cost = item\['cost'\]

self.total\_cost += cost

self.log\_message(f"本次生成费用: ${cost:.4f}")

rmb\_cost = cost \* 7.2

self.log\_message(f"本次生成费用(人民币): ¥{rmb\_cost:.2f}")

# 获取图片URL

task\_id = item.get('taskUUID')

image\_url = item.get('imageURL')

if task\_id and image\_url:

return task\_id, image\_url

self.log\_message("API响应中没有找到有效的图片URL", "ERROR")

else:

self.log\_message("API响应格式错误", "ERROR")

return None, None

except requests.exceptions.RequestException as e:

if attempt < max\_retries - 1:

self.log\_message(f"API请求失败，{retry\_delay}秒后重试 ({attempt + 1}/{max\_retries}): {str(e)}", "WARNING")

time.sleep(retry\_delay)

continue

self.log\_message(f"API请求失败: {str(e)}", "ERROR")

return None, None

except Exception as e:

self.log\_message(f"生成图片失败: {str(e)}", "ERROR")

return None, None

def save\_image(self, image\_url, image\_name):

"""保存图片到本地"""

try:

# 创建保存目录

save\_folder = self.get\_current\_save\_folder()

if not save\_folder:

return False

# 下载图片

response = requests.get(image\_url)

if response.status\_code != 200:

self.log\_message(f"下载图片失败: {response.status\_code}", "ERROR")

return False

# 保存图片

image\_path = os.path.join(save\_folder, f"{image\_name}.png")

with open(image\_path, 'wb') as f:

f.write(response.content)

self.log\_message(f"图片已保存: {image\_path}")

return True

except Exception as e:

self.log\_message(f"保存图片失败: {str(e)}", "ERROR")

return False

def process\_segment\_with\_gpt(self, segment, mode):

"""使用GPT处理段落"""

try:

if not segment:

return None

mode\_map = {

"1": "通用",

"2": "中文基督",

"3": "英文基督",

"4": "西班牙语",

"5": "恐怖故事"

}

system\_prompt = self.system\_prompts.get(mode\_map.get(mode))

if not system\_prompt:

self.log\_message(f"无效的模式: {mode}", "ERROR")

return None

messages = \[\
\
{"role": "system", "content": system\_prompt},\
\
{"role": "user", "content": segment}\
\
\]

try:

response = self.client.chat.completions.create(

model="gpt-4o-mini",

messages=messages,

temperature=0.7,

max\_tokens=2048

)

if response and response.choices:

prompt = response.choices\[0\].message.content.strip()

# 添加高质量图片关键词

quality\_keywords = ", breathtaking photograph, cinematic lighting, 8k uhd, highly detailed, photorealistic, professional photography, masterpiece, sharp focus, high quality"

prompt = prompt + quality\_keywords

return prompt

except Exception as e:

self.log\_message(f"调用GPT API失败: {str(e)}", "ERROR")

return None

except Exception as e:

self.log\_message(f"GPT处理失败: {str(e)}", "ERROR")

return None

def process\_file(self, file\_path, mode):

"""处理单个文件"""

try:

# 重置总费用

self.total\_cost = 0.0

# 设置当前文件名和开始时间

self.current\_file = file\_path

self.current\_file\_name = os.path.splitext(os.path.basename(file\_path))\[0\]

self.start\_time = time.time()

self.log\_message(f"开始处理文件: {file\_path}")

self.current\_mode = mode

# 读取文件内容

doc = Document(file\_path)

# 收集所有段落文本

paragraphs = \[\]

for para in doc.paragraphs:

text = para.text.strip()

if text: # 只添加非空段落

paragraphs.append(text)

# 合并所有文本并进行分段

full\_text = ' '.join(paragraphs)

# 清理文本：移除多余的空格和换行

full\_text = re.sub(r'\\s+', ' ', full\_text).strip()

segments = self.split\_into\_paragraphs(full\_text)

if not segments:

self.log\_message("没有找到有效的文本段落", "ERROR")

return False

self.log\_message(f"{os.path.basename(file\_path)}已被分割成 {len(segments)} 段")

# 创建保存文件夹

save\_folder = self.get\_current\_save\_folder()

if not save\_folder:

return False

# 处理每个段落

for i, segment in enumerate(segments, 1):

self.print\_progress(i, len(segments))

# 使用GPT处理文本

prompt = self.process\_segment\_with\_gpt(segment, mode)

if not prompt:

continue

# 为每个prompt生成4张图片

for j in range(4):

# 生成图片

task\_id, image\_url = self.generate\_image(prompt)

if not task\_id or not image\_url:

continue

# 保存图片，使用新的命名方式

image\_name = f"{i}\_{j+1}" # 例如：1\_1.png, 1\_2.png, 1\_3.png, 1\_4.png

if not self.save\_image(image\_url, image\_name):

continue

print() # 换行

# 显示总费用

if self.total\_cost > 0:

self.log\_message(f"总费用: ${self.total\_cost:.4f}")

rmb\_total\_cost = self.total\_cost \* 7.2

self.log\_message(f"总费用(人民币): ¥{rmb\_total\_cost:.2f}")

return True

except Exception as e:

self.log\_message(f"处理文件失败: {str(e)}", "ERROR")

return False

def select\_files(self, docx\_files):

"""选择要处理的文件"""

if not docx\_files:

self.log\_message("未找到任何docx文件")

return None, None

# 按文件名字母顺序排序（忽略大小写）

docx\_files.sort(key=lambda x: os.path.basename(x).lower())

while True:

print("\\n找到以下文件：")

for i, file\_path in enumerate(docx\_files, 1):

print(f"{i}. {os.path.basename(file\_path)}")

print("\\n输入 'q' 退出程序")

choice = input("\\n请输入要处理的文件编号（多个文件用空格分隔）: ").strip()

if choice.lower() == 'q':

return None, None

try:

# 处理多个文件选择

file\_indices = \[int(x) for x in choice.split()\]

selected\_files = \[\]

for index in file\_indices:

if 1 <= index <= len(docx\_files):

selected\_files.append(docx\_files\[index - 1\])

else:

self.log\_message(f"无效的文件编号: {index}", "ERROR")

return None, None

if selected\_files:

return selected\_files, choice

except ValueError:

self.log\_message("请输入有效的文件编号", "ERROR")

return None, None

def run(self):

"""主运行方法"""

try:

# 启动防睡眠

self.prevent\_sleep = subprocess.Popen(\['caffeinate'\])

self.log\_message("已启动防睡眠模式")

# 查找所有非临时和非隐藏的docx文件

docx\_files = \[\]

for file in os.listdir(self.rewrite\_folder):

# 排除隐藏文件和临时文件

if (file.endswith('.docx') and

not file.startswith('.') and # 隐藏文件

not file.startswith('~$') and # Word临时文件

not file.startswith('~') and # 其他临时文件

not file.endswith('.tmp')): # 临时文件扩展名

docx\_files.append(os.path.join(self.rewrite\_folder, file))

if not docx\_files:

print(f"\\n在 {self.rewrite\_folder} 中没有找到.docx文件")

print("请将要处理的文件放入此文件夹，然后重新运行程序")

return

# 选择文件

selected\_files, choice = self.select\_files(docx\_files)

if not selected\_files:

return

# 为每个文件选择处理模式

file\_modes = {}

print("\\n为每个文件选择处理模式：")

for file\_path in selected\_files:

while True:

print(f"\\n文件：{os.path.basename(file\_path)}")

print("1. 通用模式")

print("2. 基督教内容")

print("3. 英文基督教内容")

print("4. 西班牙语模式")

print("5. 恐怖故事模式")

print("0. 取消处理")

mode = input("请输入选项编号 (0/1/2/3/4/5): ").strip()

if mode == "0":

return # 用户取消处理

elif mode in \['1', '2', '3', '4', '5'\]:

file\_modes\[file\_path\] = mode

break

else:

print("无效的选项，请重试")

# 确认开始处理

print("\\n所有文件的处理模式已选择完毕：")

for file\_path, mode in file\_modes.items():

mode\_name = {

"1": "通用模式",

"2": "基督教内容",

"3": "英文基督教内容",

"4": "西班牙语模式",

"5": "恐怖故事模式"

}\[mode\]

print(f"- {os.path.basename(file\_path)}: {mode\_name}")

confirm = input("\\n是否开始处理？(y/n): ").strip().lower()

if confirm != 'y':

print("已取消处理")

return

# 开始处理所有文件

print("\\n开始处理文件...")

for file\_path, mode in file\_modes.items():

print(f"\\n正在处理：{os.path.basename(file\_path)}")

if not self.process\_file(file\_path, mode):

self.log\_message(f"处理文件 {os.path.basename(file\_path)} 失败", "ERROR")

# 显示总费用

print("\\n=== 费用统计 ===")

print(f"总费用: ${self.total\_cost:.4f}")

rmb\_total = self.total\_cost \* 7.2

print(f"总费用(人民币): ¥{rmb\_total:.2f}")

print("==============")

except Exception as e:

self.log\_message(f"运行时发生错误: {str(e)}", "ERROR")

finally:

# 关闭防睡眠

if self.prevent\_sleep:

self.prevent\_sleep.terminate()

self.log\_message("已关闭防睡眠模式")

def get\_current\_save\_folder(self):

"""获取当前保存文件夹"""

try:

if not self.current\_file\_name:

self.log\_message("当前没有处理的文件名", "ERROR")

return None

# 在图片文件夹下创建以文档名命名的子文件夹

save\_folder = os.path.join(self.image\_folder, self.current\_file\_name)

# 如果文件夹不存在，则创建

if not os.path.exists(save\_folder):

os.makedirs(save\_folder)

self.log\_message(f"创建保存文件夹: {save\_folder}")

return save\_folder

except Exception as e:

self.log\_message(f"获取保存文件夹失败: {str(e)}", "ERROR")

return None

def process\_text\_to\_images(self, content, save\_folder, mode):

"""处理文本生成图片"""

try:

# 使用GPT生成英文描述

print("正在生成英文描述...")

# 计算输入token数量（粗略估计：每个字符4个token）

input\_tokens = len(content) \* 4

completion = self.client.chat.completions.create(

model="o1-mini-2024-09-12",

messages=\[\
\
{"role": "user", "content": f"{self.system\_prompts\[mode\]}\\n\\n{content}"}\
\
\],

max\_completion\_tokens=2000

)

english\_description = completion.choices\[0\].message.content.strip()

print(f"英文描述: {english\_description}")

# 计算输出token数量和成本

output\_tokens = len(english\_description) \* 4

cost = self.calculate\_cost(input\_tokens, output\_tokens)

self.total\_cost += cost

print(f"本次调用成本: ${cost:.4f}")

print(f"累计总成本: ${self.total\_cost:.4f}")

# 使用Runware生成图片

print("正在生成图片...")

response = runware.create\_image(

prompt=english\_description,

model="flux",

n=1,

size="1024x1024",

quality="standard",

style="cinematic"

)

# 保存图片

image\_url = response.data\[0\].url

response = requests.get(image\_url)

if response.status\_code == 200:

# 生成唯一的文件名

timestamp = datetime.now().strftime("%Y%m%d\_%H%M%S")

unique\_id = str(uuid.uuid4())\[:8\]

image\_filename = f"image\_{timestamp}\_{unique\_id}.png"

image\_path = os.path.join(save\_folder, image\_filename)

# 保存图片

with open(image\_path, 'wb') as f:

f.write(response.content)

print(f"图片已保存: {image\_path}")

return True

else:

print(f"下载图片失败: {response.status\_code}")

return False

except Exception as e:

print(f"生成图片时出错: {str(e)}")

return False

if \_\_name\_\_ == "\_\_main\_\_":

generator = RunwareImageGenerator()

generator.run()
