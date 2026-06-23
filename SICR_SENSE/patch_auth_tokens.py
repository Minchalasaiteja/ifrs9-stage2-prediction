from pathlib import Path

replacements = {
    "localStorage.getItem('access_token')": 'getAuthToken()',
    'localStorage.getItem("access_token")': 'getAuthToken()',
    "localStorage.getItem('refresh_token')": 'getRefreshToken()',
    'localStorage.getItem("refresh_token")': 'getRefreshToken()'
}

files = [
    'static/js/admin.js',
    'static/js/monitoring.js',
    'static/js/dashboard.js',
    'templates/dashboard/settings.html',
    'templates/dashboard/profile.html',
    'templates/dashboard/predictions.html',
    'templates/dashboard/batch.html',
    'templates/admin/dashboard.html'
]

for file in files:
    path = Path(file)
    if not path.exists():
        print(f'MISSING {file}')
        continue
    text = path.read_text(encoding='utf-8')
    original = text
    for old, new in replacements.items():
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding='utf-8')
        print(f'Patched {file}')
    else:
        print(f'No changes in {file}')
