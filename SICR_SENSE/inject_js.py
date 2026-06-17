import os

dir_path = r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\templates'
for root, dirs, files in os.walk(dir_path):
    for f in files:
        if f.endswith('.html') and 'components' not in root:
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            if '</body>' in content and 'components.js' not in content:
                content = content.replace('</body>', '  <script src="/static/js/components.js"></script>\n</body>')
                with open(filepath, 'w', encoding='utf-8') as fh:
                    fh.write(content)
print('Injected components.js successfully')