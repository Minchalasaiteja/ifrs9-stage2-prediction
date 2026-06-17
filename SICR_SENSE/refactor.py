import os
import re

dir_paths = [
    r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\templates\dashboard',
    r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\templates\admin'
]

for dir_path in dir_paths:
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if already extending
                if '{% extends' in content:
                    continue
                
                # We need to find the start of the content. Usually right after header.html
                # Or look for <main class="flex-1 ..."> and {% include 'components/header.html' %}
                header_match = re.search(r'{%\s*include\s+[\'"]components/header\.html[\'"]\s*%}', content)
                if not header_match:
                    print(f'Could not find header include in {file}')
                    continue
                
                content_start_idx = header_match.end()
                
                # We also want to skip the <div class="p-8"> if we can, but dashboard_base.html ALREADY has <div class="p-8 space-y-8">.
                # If the original file has <div class="p-8">, we should probably strip it to avoid double padding.
                # Let's just find the first <div class="p-8..."> after header.
                p8_match = re.search(r'<div\s+class="p-8[^"]*">\s*', content[content_start_idx:])
                if p8_match:
                    # Content inside the p-8 div
                    content_start_idx += p8_match.end()
                
                # Find the end of the content. Usually before </main> or </div>\n    </main>
                # Let's search backwards for </main>
                main_end_idx = content.rfind('</main>')
                if main_end_idx == -1:
                    print(f'Could not find </main> in {file}')
                    continue
                
                # If we stripped the <div class="p-8...">, we should also strip its closing </div>
                # which is usually the last </div> before </main>
                if p8_match:
                    last_div_before_main = content.rfind('</div>', 0, main_end_idx)
                    if last_div_before_main != -1:
                        main_end_idx = last_div_before_main
                
                # Extract the core content
                core_content = content[content_start_idx:main_end_idx].strip()
                
                # Now extract any scripts that were at the bottom
                scripts_match = re.search(r'<script.*?>.*?</script>', content[main_end_idx:], re.DOTALL)
                scripts_block = ""
                if scripts_match:
                    scripts_block = "\n{% block scripts %}\n" + content[main_end_idx:][scripts_match.start():scripts_match.end()] + "\n{% endblock %}"
                
                # Wait, dashboard.html has multiple scripts at the bottom.
                # Let's just grab everything from </main> to </body> that contains <script>
                script_section = ""
                main_to_body = content[content.rfind('</main>'):content.rfind('</body>')]
                scripts_only = re.findall(r'(<script.*?>.*?</script>)', main_to_body, re.DOTALL)
                if scripts_only:
                    script_section = "\n{% block scripts %}\n" + "\n".join(scripts_only) + "\n{% endblock %}"
                
                title_match = re.search(r'<title>(.*?)</title>', content)
                title = title_match.group(1) if title_match else 'SICRSense Dashboard'
                
                new_file = f"{{% extends 'dashboard_base.html' %}}\n\n{{% block title %}}{title}{{% endblock %}}\n\n{{% block content %}}\n{core_content}\n{{% endblock %}}\n{script_section}\n"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_file)
                print(f'Refactored {file}')
