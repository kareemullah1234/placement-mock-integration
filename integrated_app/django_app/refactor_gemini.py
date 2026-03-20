import os
import glob
import re

html_files = glob.glob('*/templates/**/*.html', recursive=True)

# Replacements to mimic Google Gemini Dark Theme
replacements = {
    # Backgrounds
    r'bg-slate-900(?:/\d+)?': 'bg-[#1e1f20]',
    r'bg-slate-800(?:/\d+)?': 'bg-[#282a2c]',
    r'bg-slate-700(?:/\d+)?': 'bg-[#444746]',
    r'bg-slate-600(?:/\d+)?': 'bg-[#5f6368]',
    
    # Borders
    r'border-slate-800(?:/\d+)?': 'border-[#1e1f20]',
    r'border-slate-700(?:/\d+)?': 'border-[#444746]',
    r'border-slate-600(?:/\d+)?': 'border-[#444746]',
    
    # Texts
    r'text-slate-400': 'text-[#c4c7c5]',
    r'text-slate-500': 'text-[#8e918f]',
    r'text-slate-300': 'text-[#e3e3e3]',
    r'text-white': 'text-[#ffffff]',
    
    # Blue branding to Gemini Light Blue
    r'text-blue-500': 'text-[#a8c7fa]',
    r'text-blue-400': 'text-[#a8c7fa]',
    r'text-purple-500': 'text-[#d3e3fd]',
    r'text-purple-400': 'text-[#d3e3fd]',
    
    r'bg-blue-600/10': 'bg-[#004a77]/30',
    r'bg-blue-600/20': 'bg-[#004a77]/40',
    r'bg-blue-500/20': 'bg-[#004a77]/40',
    r'border-blue-500/20': 'border-[#a8c7fa]/30',
    r'border-blue-500/30': 'border-[#a8c7fa]/40',
    
    # Gradients mapped to Gemini gradient class
    r'bg-gradient-to-[a-z]+ from-blue-\d+ to-blue-\d+ hover:from-blue-\d+ hover:to-blue-\d+(?: border border-blue-\d+/\d+)?': 'gemini-gradient-bg border-none',
    r'bg-gradient-to-[a-z]+ from-purple-\d+ to-indigo-\d+ hover:from-purple-\d+ hover:to-indigo-\d+(?: border border-purple-\d+/\d+)?': 'gemini-gradient-bg border-none',
    r'bg-blue-600 hover:bg-blue-500': 'gemini-gradient-bg border-none',
    r'bg-slate-800 hover:bg-slate-700': 'bg-[#444746] hover:bg-[#5f6368]',
    
    # Buttons/Shadows
    r'shadow-lg': 'shadow-md shadow-black/20',
    r'shadow-xl': 'shadow-lg shadow-black/30',
    
    # Unique components
    r'fa-rocket': 'fa-sparkles',
    r'fa-user-edit': 'fa-pen-sparkle',
}

for file in html_files:
    if 'common' in file: # skip base.html as it is already pure gemini
        continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
        
    if original != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Migrated {file} to Gemini Design System")
