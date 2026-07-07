import re

with open('C:/Users/q1948/Desktop/Course/软开3/unpacked/word/document.xml', 'r', encoding='utf-8') as f:
    content = f.read()

texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', content)
for t in texts:
    print(t)
