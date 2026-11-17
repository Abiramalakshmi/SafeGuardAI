import hashlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import init_db, verify_admin

init_db()
result = verify_admin('admin', 'admin123')
print('verify_admin result:', result)

h = hashlib.sha256('admin123'.encode()).hexdigest()
print('Expected hash:', h)
