import os
import re

dir_path = r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\templates\components'
js_code = []

# Refactor error.html first to use data attributes
error_file = os.path.join(dir_path, 'error.html')
with open(error_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('<div class="glass-card max-w-lg w-full p-12 text-center relative z-10">', '<div id="error-data-container" data-code="{{ code }}" data-message="{{ message }}" data-details="{{ details|default(\'\') }}" class="glass-card max-w-lg w-full p-12 text-center relative z-10">')
# Write it back without the jinja script so it gets extracted next
with open(error_file, 'w', encoding='utf-8') as f:
    f.write(content)

for file in os.listdir(dir_path):
    if file.endswith('.html'):
        filepath = os.path.join(dir_path, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
        if match:
            script_content = match.group(1).strip()
            
            if file == 'error.html':
                script_content = """
function reportError() {
    const container = document.getElementById('error-data-container');
    if (!container) return;
    const errorInfo = {
        code: container.dataset.code,
        message: container.dataset.message,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        details: container.dataset.details
    };
    
    fetch('/api/v1/report-error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorInfo)
    })
    .then(() => {
        if(typeof toast !== 'undefined' && toast.success) toast.success('Error reported. Thank you for your feedback!');
    })
    .catch(() => {
        if(typeof toast !== 'undefined' && toast.error) toast.error('Failed to report error');
    });
}
"""
            js_code.append(f'/* === {file} === */\n{script_content}\n')
            
            # Remove from HTML
            new_content = content[:match.start()] + content[match.end():]
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content.strip() + '\n')

with open(r'c:\Users\techsupport6\Downloads\PCRM\PCRM\v4\static\js\components.js', 'w', encoding='utf-8') as f:
    f.write('\n'.join(js_code))
print('Extracted JS successfully')