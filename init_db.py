import sqlite3

# database.db naam ki file se connection banao (agar nahi hai to ban jayegi)
connection = sqlite3.connect("database.db")

# schema.sql file padho aur uske saare commands chalao
with open("schema.sql") as f:
    connection.executescript(f.read())

# Demo users daalo (testing ke liye)
cursor = connection.cursor()
cursor.execute(
    "INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
    ("admin", "admin123", "Admin User"),
)
cursor.execute(
    "INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
    ("member1", "member123", "Member One"),
)

# Changes ko save karo
connection.commit()
connection.close()

print("Database ban gaya! database.db file ready hai.")