from openai import OpenAI

import os

from docx import Document

import string

import time

import tiktoken

import openai

import re

import traceback

class TextRewriter:

    def __init__(self):
        """初始化改写器"""
        # 初始化API客户端
        # 直接在代码中设置 API key
        api_key = ""  # 请将此处替换为您的实际API密钥

        self.openai_client = OpenAI(
            base_url="https://api.openai.com/v1",
            api_key=api_key
        )

        # ====== 配置项 ======
        # 文本处理相关配置
        self.MAX_TEXT_LENGTH = 12000  # 单次处理的最大文本长度
        self.MAX_RETRIES = 5  # 最大重试次数
        self.ENABLE_SECOND_ROUND = True  # 是否启用第二轮改写

        # 改写幅度配置
        self.rewrite_ratio = {
            'min': 60,  # 最小改写幅度（百分比）
            'max': 85  # 最大改写幅度（百分比）
        }

        # 翻译模式字符比例配置
        self.translation_ratio = {
            'min': 100,  # 最小字符比例（百分比）
            'max': 400  # 最大字符比例（百分比）
        }

        # 英文到中文翻译字符比例配置
        self.en_to_cn_ratio = {
            'min': 20,  # 最小字符比例（百分比）
            'max': 100  # 最大字符比例（百分比）
        }

        # 模型配置
        self.MODEL_CONFIG = {
            # 微调模型配置
            'ft_model': {
                'name': "ft:gpt-4o-mini-2024-07-18:personal:",  # 模型名称
                'temperature': 0.9  # 温度参数
            },
            # GPT-4模型配置
            'gpt4o_model': {
                'name': "gpt-4o-mini-2024-07-18",  # 模型名称
                'temperature': {
                    'default': 0.75,  # 默认温度
                    'translation': 0.7,  # 翻译模式温度
                    'min': 0.2,  # 最小温度
                    'step': 0.1  # 每次重试减少的温度值
                },
                'max_length': 16000,  # 最大长度
                'max_tokens': 16000  # 最大token数
            }
        }

        # API配置
        self.claude_client = OpenAI(
            base_url="",
            api_key=""
        )

        # ====== 提示词配置 ======
        # 英文基督教内容提示词
        self.en_christian_prompt = """You are a professional Christian content editor. Your task is to rewrite the given English text with the following requirements:

1. Content Requirements:
- Maintain biblical accuracy
- Make the language more vivid and easy to understand
2. Improve the clarity and fluency of the article, which can be adjusted from the original text, and must be significantly different from the original text
3. Correct all typos and grammatical errors, without any content in parentheses
4. Only provide the rewritten content, without explanation"""

        # 中文基督教内容提示词
        self.cn_christian_prompt = """你是一位基督教专家。你的任务是改写给定的文本，要求：

1. 使语言更加生动易懂
2. 改善文章的清晰度和流畅性，可以对原文进行删减和调整，要和原文明显不一样
3. 修正所有错别字和语法错误，不要有括号内容
4. 只提供改写后的内容，无需解释"""

        # 通用内容提示词
        self.general_prompt = """你是一位内容编辑专家。你的任务是改写给定的文本，要求：

1. 使语言更加生动易懂
2. 改善文章的清晰度和流畅性，可对原文进行删减和调整，要和原文明显不一样，相似度不能高于5%
3. 修正所有错别字和语法错误，不要有括号内容
4. 只提供改写后的内容，无需解释"""

        # 提取主题改写提示词
        self.topic_extraction_prompt = """你是一位内容编辑专家。你的任务是改写给定的文本，要求：

1. 将文本的大纲进行提取，要保证日期时间和引用内容的准确性
2. 根据文章大纲进行重写，文章逻辑要清晰流畅
3. 不要有错别字和语法错误，不要有括号内容
4. 只提供改写后的内容，无需解释"""

        # 西班牙语翻译提示词
        self.spanish_prompt = """Por favor, traduce el siguiente texto al español. Requisitos:

1. Mantén el significado original y todos los detalles del texto
2. Asegúrate de que la traducción sea precisa y completa
3. Mantén un tono profesional y natural
4. Conserva toda la terminología técnica y específica
5. Mantén la misma estructura y organización del texto original
6. La traducción debe ser fiel al original, sin omitir ni agregar información
7. Utiliza expresiones naturales en español manteniendo el mismo nivel de formalidad

Importante: La traducción debe ser detallada y mantener todos los matices del texto original."""

        # 中文到英文翻译提示词
        self.chinese_to_english_prompt = """You are a professional translator. Your task is to translate the given Chinese text into English with the following requirements:

1. Translation Requirements:
- Make the language vivid and easy to understand
- Improve the clarity and fluency while maintaining the original meaning
- Use natural and idiomatic English expressions
2. Content Requirements:
- Maintain accuracy of all details and technical terms
- Remove any content in parentheses or special symbols
- Fix any typos or grammatical errors
3. Only provide the translated content in English, without any explanations or notes"""

        # 英文到中文翻译提示词
        self.english_to_chinese_prompt = """你是一位翻译改写专家。你的任务是将给定的文本翻译并微调，要求：

1. 使翻译后的语言更加生动易懂 符合中文语境
2. 改善文章的清晰度和流畅性
3. 修正所有错别字和语法错误，不要有括号内容
4. 只提供改写后的内容，无需解释"""

        # GPT-4 本地化改写提示词
        self.gpt4_localization_prompt = """You are a professional content editor. Your task is to rewrite the given Chinese text with the following requirements:

1. Content Requirements:
- Replace Chinese place names and person names noun concepts in the text,with common American names for better understanding by American audience
- Make the language more vivid and easy to understand
2. Improve the clarity and fluency of the article, which can be adjusted from the original text
3. Correct all typos and grammatical errors, without any content in parentheses
4. 在满足上述条件后，将中文全部翻译成英文
5. Only provide the rewritten content, without explanation"""

        # 第二轮改写提示词
        self.general_prompt_round2 = """你是一位内容编辑专家。你的任务是将给定的文本进行纠错，要求：

1. 使语言更加易懂，修正所有错别字和语法错误
2. 只提供改写后的内容，无需解释
"""

        # 第二轮基督教内容提示词
        self.cn_christian_prompt_round2 = """你是一位基督教专家。你的任务是纠错给定的文本，要求：

1. 使语言更加易懂，修正所有错别字和语法错误
2. 只提供改写后的内容，无需解释
"""

    def read_docx(self, file_path):
        """读取docx文件内容"""
        try:
            doc = Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:  # 只添加非空段落
                    paragraphs.append(text)
            return '\n'.join(paragraphs)
        except Exception as e:
            print(f"读取文件时出错: {str(e)}")
            return None

    def save_to_docx(self, text, file_path):
        """保存内容到docx文件"""
        try:
            doc = Document()
            # 将文本按换行符分割成段落
            paragraphs = text.split('\n')
            for para in paragraphs:
                if para.strip():  # 只添加非空段落
                    doc.add_paragraph(para.strip())
            doc.save(file_path)
            return True
        except Exception as e:
            print(f"保存文件时出错: {str(e)}")
            return False

    def get_unique_filename(self, base_path):
        """获取唯一的文件名，如果文件存在则在文件名后加上数字"""
        try:
            # 确保输出到"改写"文件夹
            rewrite_folder = os.path.join(os.path.expanduser("~/Desktop"), "剪辑/改写")
            if not os.path.exists(rewrite_folder):
                os.makedirs(rewrite_folder)

            # 获取原始文件名和扩展名
            filename = os.path.basename(base_path)
            name, ext = os.path.splitext(filename)

            # 生成新的文件路径
            counter = 1
            new_path = os.path.join(rewrite_folder, f"{name}{ext}")
            while os.path.exists(new_path):
                new_path = os.path.join(rewrite_folder, f"{name}_{counter}{ext}")
                counter += 1

            return new_path
        except Exception as e:
            print(f"生成文件名时出错: {str(e)}")
            return None

    def get_docx_files(self):
        """获取改写文件夹中的docx文件"""
        try:
            # 确保桌面上的"改写"文件夹存在
            rewrite_folder = os.path.join(os.path.expanduser("~/Desktop"), "剪辑/改写")
            if not os.path.exists(rewrite_folder):
                os.makedirs(rewrite_folder)
                print(f'已创建文件夹：{rewrite_folder}')
                print('请将要处理的文件放入此文件夹，然后重新运行程序')
                return []

            # 获取文件夹中的所有非隐藏的docx文件
            docx_files = []
            for file in os.listdir(rewrite_folder):
                # 跳过隐藏文件和临时文件
                if (not file.startswith('.') and not file.startswith('~')) and file.endswith('.docx'):
                    file_path = os.path.join(rewrite_folder, file)
                    if os.path.isfile(file_path):
                        docx_files.append((file, file_path))

            if not docx_files:
                print(f'在 {rewrite_folder} 中没有找到.docx文件')
                print('请将要处理的文件放入此文件夹，然后重新运行程序')
                return []

            # 按自然排序对文件进行排序
            docx_files.sort(key=lambda x: self.natural_sort_key(x[0]))

            # 显示找到的文件
            print("\n找到以下文件：")
            for i, (filename, _) in enumerate(docx_files, 1):
                print(f"{i}. {filename}")
            print()

            return docx_files
        except Exception as e:
            print(f"获取文件列表时出错: {str(e)}")
            traceback.print_exc()  # 打印详细的错误信息
            return []

    def count_tokens(self, text):
        """使用tiktoken准确计算token数量"""
        if text is None:
            return 0
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(str(text)))  # 确保text是字符串
        except Exception as e:
            print(f"Token计算失败: {str(e)}")
            # 如果tiktoken失败，使用简单估算（每4个字符约1个token）
            return len(str(text)) // 4

    def calculate_cost(self, input_tokens, output_tokens, is_finetune=False):
        """计算API调用成本"""
        if input_tokens is None or output_tokens is None:
            return 0
        if is_finetune:
            # 微调模型的价格（每1M token）
            input_price = 0.3 / 1000000 # 输入价格 ($0.3/1M tokens)
            output_price = 1.2 / 1000000 # 输出价格 ($1.2/1M tokens)
        else:
            # GPT-4的价格（每1M token）
            input_price = 0.15 / 1000000 # 输入价格 ($0.15/1M tokens)
            output_price = 0.6 / 1000000 # 输出价格 ($0.6/1M tokens)
        return (input_tokens * input_price + output_tokens * output_price)

    def split_text_by_length(self, text, max_length=None):
        """将文本按长度分段"""
        if max_length is None:
            max_length = self.MODEL_CONFIG['gpt4o_model']['max_length']
        segments = []
        current_segment = ""
        for paragraph in text.split('\n'):
            if len(current_segment) + len(paragraph) + 1 <= max_length:
                current_segment += (paragraph + '\n')
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = paragraph + '\n'
        if current_segment:
            segments.append(current_segment.strip())
        return segments

    def process_segment(self, text, mode):
        """处理单个文本段落"""
        import time
        # 确保mode是整数
        mode = int(mode)
        # 生成提示词
        if mode == 1: # 通用模式
            if hasattr(self, 'is_second_round') and self.is_second_round:
                prompt = f"{self.general_prompt_round2}\n\n请改写以下文本：\n\n{text}"
            else:
                prompt = self.general_prompt + "\n\n" + text
        elif mode == 2: # 中文到英文翻译
            prompt = f"{self.chinese_to_english_prompt}\n\n请翻译以下文本：\n\n{text}"
        elif mode == 3: # 英文本地化人地名改写
            prompt = f"{self.gpt4_localization_prompt}\n\n请改写以下文本：\n\n{text}"
        elif mode == 4: # 英文到中文翻译
            prompt = f"{self.english_to_chinese_prompt}\n\n请翻译以下英文文本：\n\n{text}"
        elif mode == 5: # 提取主题改写
            if hasattr(self, 'is_second_round') and self.is_second_round:
                prompt = f"{self.general_prompt_round2}\n\n请改写以下文本：\n\n{text}"
            else:
                prompt = f"{self.topic_extraction_prompt}\n\n请改写以下文本：\n\n{text}"
        else:
            print(f"错误：不支持的处理模式 {mode}")
            return None, 0

        try:
            # 根据重试次数调整temperature
            current_temp = max(
                self.MODEL_CONFIG['gpt4o_model']['temperature']['min'],
                self.MODEL_CONFIG['gpt4o_model']['temperature']['default'] -
                0 * self.MODEL_CONFIG['gpt4o_model']['temperature']['step']
            )
            print("\nGPT-4处理中...")
            start_time = time.time()
            # 调用API
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_CONFIG['gpt4o_model']['name'],
                messages=[{"role": "user", "content": prompt}],
                temperature=current_temp,
                max_tokens=self.MODEL_CONFIG['gpt4o_model']['max_tokens']
            )
            process_time = time.time() - start_time
            print(f"GPT-4处理完成，耗时: {process_time:.2f}秒")
            # 获取生成的内容
            content = response.choices[0].message.content.strip()
            # 计算token和成本
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(input_tokens, output_tokens)
            print(f"\n第 {1} 次尝试:")
            print(f"使用模型: {self.MODEL_CONFIG['gpt4o_model']['name']}")
            print(f"本次调用成本: ${cost:.4f}")
            print(f"Token估算 - 输入: {input_tokens}, 输出: {output_tokens}")
            return content, cost
        except Exception as e:
            print(f"处理出错: {str(e)}")
            return None, 0

    def process_file(self, filepath, mode):
        """处理单个文件"""
        print(f"\n开始处理文件: {filepath}")
        total_cost = 0
        # 检查文件
        if not os.path.exists(filepath):
            print("文件不存在")
            return False, 0, 0
        print(f"文件是否存在: {os.path.exists(filepath)}")
        print(f"文件是否可读: {os.access(filepath, os.R_OK)}")
        print(f"文件大小: {os.path.getsize(filepath)} 字节")
        try:
            print("\n尝试读取文件内容...")
            content = self.read_docx(filepath)
            if not content:
                print("文件内容为空")
                return False, 0, 0
            original_chars = len(content)
            print(f"成功读取文件，字符数: {original_chars}")
            print(f"内容预览（前100字符）: {content[:100]}")
            # 处理逻辑
            if int(mode) in [1, 5]: # 通用模式和提取主题改写模式
                print(f"\n开始微调模型改写，文本长度: {len(content)} 字符")
                # 第一轮：微调模型处理
                first_result = self.process_with_finetune(content, int(mode))
                if not first_result:
                    print("微调模型处理失败")
                    if int(mode) == 1: # 如果是模式1，且5次生成都失败，则不进行二次改写
                        print("模式1中5次生成都失败，不进行二次改写，处理结束")
                        return False, total_cost, 0
                    else:
                        print("跳过微调模型，直接使用GPT-4处理")
                    base_length = len(content) # 使用原始长度作为基准
                else:
                    if self.ENABLE_SECOND_ROUND:
                        print("\n开始GPT-4第二轮改写...")
                        self.is_second_round = True # 标记为第二轮
                        base_length = len(first_result) # 使用微调模型处理后的长度作为基准
                        content = first_result
                    else:
                        print("第二轮改写已禁用，将使用微调模型的处理结果")
                        content = first_result
                    # 保存微调模型处理结果
                    output_path = self.save_to_docx(content, self.get_unique_filename(filepath))
                    if output_path:
                        print(f"\n处理完成，结果已保存至: {output_path}")
                        return True, total_cost, len(content)
                    else:
                        base_length = len(content) # 其他模式使用原始长度作为基准
            # 分段处理
            segments = self.split_text_by_length(content)
            print(f"\n文本已分为 {len(segments)} 段")
            processed_segments = []
            for i, segment in enumerate(segments, 1):
                print(f"\n开始处理第 {i}/{len(segments)} 段:")
                processed_text, cost = self.process_segment(segment, mode)
                if processed_text:
                    processed_segments.append(processed_text)
                    total_cost += cost
                else:
                    print(f"处理第 {i} 段失败")
                    return False, total_cost, 0
            # 合并处理后的内容
            final_content = "\n".join(processed_segments)
            # 保存结果
            output_path = self.save_to_docx(final_content, self.get_unique_filename(filepath))
            if output_path:
                print(f"\n处理完成，结果已保存至: {output_path}")
                print(f"总成本: ${total_cost:.4f}")
                return True, total_cost, len(final_content)
            return False, total_cost, 0
        except Exception as e:
            print(f"处理文件时出错: {str(e)}")
            return False, total_cost, 0

    def select_mode(self, file_name):
        """为单个文件选择处理模式"""
        while True:
            print(f"\n请为文件 {file_name} 选择处理模式:")
            print("1. 通用模式（先微调后GPT-4）")
            print("2. 中文到英文翻译（仅GPT-4）")
            print("3. 英文本地化人地名改写（仅GPT-4）")
            print("4. 英文到中文翻译（仅GPT-4）")
            print("5. 提取主题改写（先微调后GPT-4）")
            choice = input("\n请输入模式编号(1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                print(f"已选择模式 {choice}")
                return choice
            else:
                print("无效的选择，请重试")

    def natural_sort_key(self, file_tuple):
        import re
        file_name = file_tuple[0]
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return alphanum_key(file_name)

    def process_files(self, files, modes):
        """处理多个文件"""
        results = []
        total_chars = 0
        total_rewritten_chars = 0
        total_cost = 0
        success_count = 0
        for i, (filename, filepath) in enumerate(files, 1):
            print(f"\n处理文件 {i}/{len(files)}: {filename}")
            try:
                mode = modes.get(filename)
                if not mode:
                    print(f"未找到文件 {filename} 的处理模式")
                    continue
                print(f"完整文件路径: {filepath}")
                print(f"选择的处理模式: {mode}")
                success, cost, chars = self.process_file(filepath, mode)
                if success:
                    success_count += 1
                    total_chars += chars
                    # 获取改写后的字符数
                    output_path = self.get_latest_output_path()
                    if output_path and os.path.exists(output_path):
                        try:
                            # 使用python-docx读取文件内容
                            doc = Document(output_path)
                            rewritten_text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                            rewritten_chars = len(rewritten_text)
                            total_rewritten_chars += rewritten_chars
                            results.append({
                                'filename': filename,
                                'original_chars': chars,
                                'rewritten_chars': rewritten_chars,
                                'success': True
                            })
                        except Exception as e:
                            print(f"读取输出文件时出错: {str(e)}")
                            results.append({
                                'filename': filename,
                                'original_chars': chars,
                                'rewritten_chars': 0,
                                'success': False
                            })
                    else:
                        print(f"无法读取输出文件: {output_path}")
                        results.append({
                            'filename': filename,
                            'original_chars': chars,
                            'rewritten_chars': 0,
                            'success': False
                        })
                else:
                    results.append({
                        'filename': filename,
                        'original_chars': chars,
                        'rewritten_chars': 0,
                        'success': False
                    })
                total_cost += cost
            except Exception as e:
                print(f"处理文件时出错: {str(e)}")
                traceback.print_exc()
                results.append({
                    'filename': filename,
                    'original_chars': 0,
                    'rewritten_chars': 0,
                    'success': False
                })
        # 打印处理结果
        print("\n处理完成!")
        print(f"成功: {success_count}/{len(files)}")
        # 打印字符统计表格
        print("\n字符统计:")
        print("-" * 100)
        print(f"{'文件名':<40} {'原文字符':<16} {'改写字符':<16} {'变化比例':<12} {'状态':<8}")
        print("-" * 100)
        for result in results:
            filename = result['filename']
            original = result['original_chars']
            rewritten = result['rewritten_chars']
            ratio = (rewritten / original * 100) if original > 0 else 0.0
            status = "成功" if result['success'] else "失败"
            print(f"{filename:<40} {original:<16} {rewritten:<16} {ratio:.1f}% {status:<8}")
        print("-" * 100)
        print("总计:")
        print(f"原文总字符: {total_chars}")
        print(f"改写总字符: {total_rewritten_chars}")
        total_ratio = (total_rewritten_chars / total_chars * 100) if total_chars > 0 else 0.0
        print(f"总体变化比例: {total_ratio:.1f}%")
        print(f"总成本: ${total_cost:.4f}")

    def get_latest_output_path(self):
        """获取最新的输出文件路径"""
        try:
            rewrite_folder = os.path.join(os.path.expanduser("~/Desktop"), "改写")
            if not os.path.exists(rewrite_folder):
                return None
            files = [f for f in os.listdir(rewrite_folder) if f.endswith('.docx')]
            if not files:
                return None
            files.sort(key=lambda x: os.path.getmtime(os.path.join(rewrite_folder, x)), reverse=True)
            return os.path.join(rewrite_folder, files[0])
        except Exception as e:
            print(f"获取最新输出文件路径时出错: {str(e)}")
            return None

    def generate_prompt(self, text, mode):
        """根据模式生成提示词"""
        mode = int(mode)
        if mode == 1: # 通用模式
            if hasattr(self, 'is_second_round') and self.is_second_round:
                return f"{self.general_prompt_round2}\n\n请改写以下文本：\n\n{text}"
            else:
                return self.general_prompt + "\n\n" + text
        elif mode == 2: # 中文到英文翻译
            return f"{self.chinese_to_english_prompt}\n\nPlease translate the following Chinese text into English:\n\n{text}"
        elif mode == 3: # 英文本地化人地名改写
            return f"{self.gpt4_localization_prompt}\n\nPlease rewrite the following text:\n\n{text}"
        elif mode == 4: # 英文到中文翻译
            return f"{self.english_to_chinese_prompt}\n\n请翻译以下英文文本：\n\n{text}"
        elif mode == 5: # 提取主题改写
            return f"{self.topic_extraction_prompt}\n\n请改写以下文本：\n\n{text}"

    def process_with_finetune(self, content, mode):
        """使用微调模型处理内容"""
        total_cost = 0
        for attempt in range(self.MAX_RETRIES):
            try:
                print(f"\n第 {attempt + 1} 次尝试使用微调模型...")
                # 生成提示词
                prompt = self.generate_prompt(content, mode)
                # 调用API
                response = self.openai_client.chat.completions.create(
                    model=self.MODEL_CONFIG['ft_model']['name'],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.MODEL_CONFIG['ft_model']['temperature']
                )
                # 获取生成的内容
                result = response.choices[0].message.content.strip()
                # 计算token和成本
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                cost = self.calculate_cost(input_tokens, output_tokens, is_finetune=True)
                total_cost += cost
                print(f"使用模型: {self.MODEL_CONFIG['ft_model']['name']}")
                print(f"Token使用 - 输入: {input_tokens}, 输出: {output_tokens}")
                print(f"本次成本: ${cost:.4f}")
                print(f"累计成本: ${total_cost:.4f}")
                # 检查长度
                original_length = len(content)
                result_length = len(result)
                min_length = int(original_length * (self.rewrite_ratio['min'] / 100)) # 将百分比转换为小数
                max_length = int(original_length * (self.rewrite_ratio['max'] / 100))
                print(f"原文长度: {original_length} 字符")
                print(f"改写长度: {result_length} 字符")
                print(f"长度要求: {min_length}-{max_length} 字符")
                print(f"达标率: {(result_length / original_length * 100):.1f}%")
                if result_length < min_length or result_length > max_length:
                    if attempt < self.MAX_RETRIES - 1:
                        print(f"生成的内容长度{'不足' if result_length < min_length else '超出限制'}，正在重试...")
                        continue
                    else:
                        print(f"\n已达到最大重试次数 ({self.MAX_RETRIES})，微调模型处理失败")
                        return None
                print("微调模型处理成功")
                return result
            except Exception as e:
                print(f"微调模型处理出错: {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    print("正在重试...")
                    continue
                else:
                    print(f"\n已达到最大重试次数 ({self.MAX_RETRIES})，微调模型处理失败")
                    return None
        return None

    def run(self):
        """主运行方法"""
        while True:
            # 获取所有docx文件
            docx_files = self.get_docx_files()
            if not docx_files:
                return
            # 显示当前配置并让用户选择是否启用第二轮改写
            print("\n是否启用第二轮改写? (y/n)")
            self.ENABLE_SECOND_ROUND = input().lower() == 'y'
            print(f"已{'启用' if self.ENABLE_SECOND_ROUND else '禁用'}第二轮改写")
            # 获取用户选择
            choice = input("\n请输入要处理的文件编号（多个文件用空格分隔，输入q退出）: ").strip()
            if choice.lower() == 'q':
                break
            try:
                # 解析用户选择
                selected_indices = [int(x) - 1 for x in choice.split()]
                selected_files = []
                modes = {}
                # 验证选择的有效性
                for idx in selected_indices:
                    if 0 <= idx < len(docx_files):
                        selected_files.append(docx_files[idx])
                    else:
                        print(f"无效的文件编号: {idx + 1}")
                        continue
                if not selected_files:
                    print("未选择任何文件")
                    continue
                print("\n为每个文件选择处理模式...")
                print("\n文件 1/1\n")
                # 为每个选中的文件选择处理模式
                for filename, filepath in selected_files:
                    while True:
                        print(f"\n为文件 {filename} 选择处理模式：")
                        print("1. 通用模式（先微调后GPT-4）")
                        print("2. 中文到英文翻译（仅GPT-4）")
                        print("3. 英文本地化人地名改写（仅GPT-4）")
                        print("4. 英文到中文翻译（仅GPT-4）")
                        print("5. 提取主题改写（先微调后GPT-4）")
                        print("q. 跳过此文件")
                        mode = input("\n请输入模式编号（1-5，或q跳过）: ").strip()
                        if mode.lower() == 'q':
                            break
                        if mode in ['1', '2', '3', '4', '5']:
                            modes[filename] = mode # 使用filename作为键
                            break
                        print("无效的选择，请重试")
                # 显示选择的文件和模式
                print("\n已选择 {} 个文件处理，{} 个文件跳过".format(
                    len(modes), len(selected_files) - len(modes)))
                if modes:
                    print("\n选择的处理模式：")
                    for filename, _ in selected_files:
                        if filename in modes:
                            print(f"{filename}: {modes[filename]}")
                    # 确认开始处理
                    if input("\n确认开始处理？(y/n): ").lower() == 'y':
                        self.process_files(selected_files, modes)
                    break # 处理完成后退出循环
                else:
                    print("已取消处理")
            except ValueError:
                print("输入无效，请重试")
            except Exception as e:
                print(f"发生错误: {str(e)}")
                traceback.print_exc()

if __name__ == "__main__":
    rewriter = TextRewriter()
    rewriter.run()
