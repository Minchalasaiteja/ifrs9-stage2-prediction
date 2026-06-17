import os

filepath = r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\templates\index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace nav
nav_start = content.find('<nav')
nav_end = content.find('</nav>') + len('</nav>')
if nav_start != -1 and nav_end != -1:
    content = content[:nav_start] + "{% include 'components/navbar.html' %}" + content[nav_end:]

# Replace footer
footer_start = content.find('<footer')
footer_end = content.find('</footer>') + len('</footer>')
if footer_start != -1 and footer_end != -1:
    content = content[:footer_start] + "{% include 'components/footer.html' %}" + content[footer_end:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Refactored index.html to use components')