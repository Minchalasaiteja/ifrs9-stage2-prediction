import os
import re

dir_path = r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\templates\dashboard'

for file in ['monitoring.html', 'ifrs9-workflow.html']:
    filepath = os.path.join(dir_path, file)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. find the end of the <header ...> tag
    header_start = content.find('<header')
    header_end = content.find('</header>') + len('</header>')
    
    p8_match = None
    if header_start != -1 and header_end != -1:
        # 2. find <div class="p-8...">
        p8_match = re.search(r'<div\s+class="p-8[^"]*">\s*', content[header_end:])
        if p8_match:
            content_start_idx = header_end + p8_match.end()
        else:
            content_start_idx = header_end
    else:
        main_start = content.find('<main')
        content_start_idx = content.find('>', main_start) + 1
        p8_match = re.search(r'<div\s+class="p-8[^"]*">\s*', content[content_start_idx:])
        if p8_match:
            content_start_idx += p8_match.end()
    
    # Let's search backwards for </main>
    main_end_idx = content.rfind('</main>')
    if main_end_idx == -1:
        main_end_idx = content.rfind('</body>')
    
    if p8_match:
        last_div = content.rfind('</div>', 0, main_end_idx)
        if last_div != -1:
            main_end_idx = last_div
    
    core_content = content[content_start_idx:main_end_idx].strip()
    
    # Also extract styles that might be in the head and put them in block extra_css
    styles_match = re.search(r'<style>(.*?)</style>', content[:content.find('</head>')], re.DOTALL)
    extra_css = ''
    if styles_match:
        css = styles_match.group(1).strip()
        # Remove the base CSS variables which we already have in base.html
        css = re.sub(r':root\s*\{[^}]*\}', '', css, flags=re.DOTALL)
        css = re.sub(r'\*\s*\{\s*margin:\s*0;\s*padding:\s*0;\s*box-sizing:\s*border-box;\s*\}', '', css)
        css = re.sub(r'body\s*\{[^}]*\}', '', css, flags=re.DOTALL)
        css = re.sub(r'\.glass-card\s*\{[^}]*\}', '', css, flags=re.DOTALL)
        css = re.sub(r'\.glass-card:hover\s*\{[^}]*\}', '', css, flags=re.DOTALL)
        if css.strip():
            extra_css = f'{{% block extra_css %}}\n<style>\n{css.strip()}\n</style>\n{{% endblock %}}\n\n'
    
    title_match = re.search(r'<title>(.*?)</title>', content)
    title = title_match.group(1) if title_match else 'SICRSense'
    
    if file == 'monitoring.html' and header_start != -1:
        custom_header = content[header_start:header_end]
        core_content = custom_header + '\n' + core_content
    elif file == 'ifrs9-workflow.html' and header_start != -1:
        custom_header = content[header_start:header_end]
        core_content = custom_header + '\n' + core_content
    
    body_start = content.find('<body')
    all_scripts = re.findall(r'(<script.*?>.*?</script>)', content[body_start:], re.DOTALL)
    # Filter out external
    local_scripts = [s for s in all_scripts if 'src=' not in s or '/static/' in s]
    script_section = ''
    if local_scripts:
        script_section = '\n{% block scripts %}\n' + '\n'.join(local_scripts) + '\n{% endblock %}\n'
    
    new_file = f"{{% extends 'dashboard_base.html' %}}\n{{% block title %}}{title}{{% endblock %}}\n\n{extra_css}{{% block content %}}\n{core_content}\n{{% endblock %}}\n{script_section}"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_file)
    print(f'Refactored {file}')
