from string import Template


translate_template = Template("""请将以下文本翻译为${target_lang}，直接输出翻译结果，不要进行任何解释。

${text}
""")
