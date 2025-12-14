"""
Fix Socket.IO CORS configuration by adding 127.0.0.1:2003
"""

file_path = r"d:\bishe\one\backend\app\services\socket_manager.py"

# Read file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace CORS configuration
old_line = "    cors_allowed_origins=['http://localhost:2003', 'http://localhost:5173'],"
new_line = "    cors_allowed_origins=['http://localhost:2003', 'http://127.0.0.1:2003', 'http://localhost:5173'],"

if old_line in content:
    content = content.replace(old_line, new_line)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully updated CORS configuration!")
    print("Added http://127.0.0.1:2003 to allowed origins")
else:
    print("❌ Could not find the line to replace")
    print("Current CORS line might have already been modified")
