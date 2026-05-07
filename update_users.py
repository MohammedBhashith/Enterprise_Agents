from database import get_connection

conn = get_connection()
cur = conn.cursor()

# Update EMP001
cur.execute("""
UPDATE users
SET name = ?, email = ?
WHERE user_id = ?
""", ("Bhashith", "Mohammed.Bhashith@novigosolutions.com", "EMP001"))

# Update MGR001
cur.execute("""
UPDATE users
SET name = ?, email = ?, department = ? 
WHERE user_id = ?
""", ("Hisham", "mohdbhashith313@gmail.com", "Manager Team", "MGR001"))

# Update MGR001
cur.execute("""
UPDATE users
SET name = ?, email = ?
WHERE user_id = ?
""", ("John","mohdbhashith313@gmail.com", "IT001"))

cur.execute("""
UPDATE users
SET name = ?, email = ? , department = ?
WHERE user_id = ?
""", ("Aman","Mohammed.Bhashith@novigosolutions.com","Engineering", "EMP002"))


conn.commit()
conn.close()

print("Users updated successfully.")