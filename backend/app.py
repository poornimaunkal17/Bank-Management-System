from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)


# ----------------------------
# SERVE FRONTEND
# ----------------------------

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')


# ----------------------------
# MYSQL CONNECTION
# ----------------------------

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Poorni@17",
        database="bankdb1"
    )


# ----------------------------
# LOGIN
# ----------------------------

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        if not data or not data.get('username') or not data.get('password'):
            return jsonify({"success": False, "message": "Username and password required"}), 400

        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (data['username'], data['password'])
        )
        admin = cursor.fetchone()
        cursor.close()
        db.close()

        if admin:
            return jsonify({"success": True, "message": "Login Success"})

        return jsonify({"success": False, "message": "Invalid Credentials"})

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------
# CREATE ACCOUNT
# ----------------------------

@app.route('/create-account', methods=['POST'])
def create_account():
    try:
        data = request.get_json()
        print("CREATE ACCOUNT DATA:", data)

        if not data.get('name') or not data.get('email') or data.get('balance') is None:
            return jsonify({"success": False, "message": "Name, email, and balance are required"}), 400

        try:
            balance = float(data['balance'])
            if balance < 0:
                return jsonify({"success": False, "message": "Balance cannot be negative"})
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Balance must be a number"}), 400

        db     = get_db()
        cursor = db.cursor(dictionary=True)

        # Check duplicate email
        email = data['email'].strip().lower()
        cursor.execute("SELECT id FROM accounts WHERE email=%s", (email,))
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            db.close()
            return jsonify({
                "success": False,
                "message": f"Email already exists (Account ID: {existing['id']})"
            })

        cursor.close()
        cursor = db.cursor()

        # Insert — only columns that exist: id, name, email, balance
        cursor.execute(
            "INSERT INTO accounts (name, email, balance) VALUES (%s, %s, %s)",
            (data['name'].strip(), email, balance)
        )
        db.commit()

        account_id = cursor.lastrowid
        print("ACCOUNT CREATED:", account_id)

        cursor.close()
        db.close()

        return jsonify({
            "success": True,
            "account_id": account_id,
            "message": f"Account created! ID is {account_id}"
        })

    except Exception as e:
        print("CREATE ACCOUNT ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------
# GET ALL ACCOUNTS
# ----------------------------

@app.route('/accounts', methods=['GET'])
def get_accounts():
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT id, name, email, balance FROM accounts ORDER BY id DESC")
        accounts = cursor.fetchall()
        cursor.close()
        db.close()

        for acc in accounts:
            acc['balance'] = float(acc['balance'])

        return jsonify(accounts)

    except Exception as e:
        print("GET ACCOUNTS ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# ----------------------------
# DEPOSIT
# ----------------------------

@app.route('/deposit', methods=['POST'])
def deposit():
    try:
        data = request.get_json()
        print("DEPOSIT DATA:", data)

        if not data.get('id') or not data.get('amount'):
            return jsonify({"success": False, "message": "Account ID and amount required"}), 400

        account_id = int(data['id'])
        amount     = float(data['amount'])

        if amount <= 0:
            return jsonify({"success": False, "message": "Amount must be greater than 0"})

        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM accounts WHERE id=%s", (account_id,))
        account = cursor.fetchone()

        if not account:
            cursor.close()
            db.close()
            return jsonify({"success": False, "message": f"No account found with ID {account_id}"})

        new_balance = float(account['balance']) + amount

        # Update accounts table
        cursor.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, account_id))

        # Save to deposits table
        cursor.execute(
            "INSERT INTO deposits (account_id, amount) VALUES (%s, %s)",
            (account_id, amount)
        )

        # Save to transactions table
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount) VALUES (%s, %s, %s)",
            (account_id, "DEPOSIT", amount)
        )

        db.commit()
        cursor.close()
        db.close()

        print(f"DEPOSIT SUCCESS: Account {account_id}, Amount {amount}, New Balance {new_balance}")

        return jsonify({
            "success": True,
            "balance": new_balance,
            "message": f"Deposit of Rs.{amount:.2f} successful. New balance: Rs.{new_balance:.2f}"
        })

    except Exception as e:
        print("DEPOSIT ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------
# WITHDRAW
# ----------------------------

@app.route('/withdraw', methods=['POST'])
def withdraw():
    try:
        data = request.get_json()
        print("WITHDRAW DATA:", data)

        if not data.get('id') or not data.get('amount'):
            return jsonify({"success": False, "message": "Account ID and amount required"}), 400

        account_id = int(data['id'])
        amount     = float(data['amount'])

        if amount <= 0:
            return jsonify({"success": False, "message": "Amount must be greater than 0"})

        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM accounts WHERE id=%s", (account_id,))
        account = cursor.fetchone()

        if not account:
            cursor.close()
            db.close()
            return jsonify({"success": False, "message": f"No account found with ID {account_id}"})

        balance = float(account['balance'])

        if amount > balance:
            cursor.close()
            db.close()
            return jsonify({
                "success": False,
                "message": f"Insufficient balance. Available: Rs.{balance:.2f}"
            })

        new_balance = balance - amount

        # Update accounts table
        cursor.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, account_id))

        # Save to withdrawals table
        cursor.execute(
            "INSERT INTO withdrawals (account_id, amount) VALUES (%s, %s)",
            (account_id, amount)
        )

        # Save to transactions table
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount) VALUES (%s, %s, %s)",
            (account_id, "WITHDRAW", amount)
        )

        db.commit()
        cursor.close()
        db.close()

        print(f"WITHDRAW SUCCESS: Account {account_id}, Amount {amount}, New Balance {new_balance}")

        return jsonify({
            "success": True,
            "balance": new_balance,
            "message": f"Withdrawal of Rs.{amount:.2f} successful. New balance: Rs.{new_balance:.2f}"
        })

    except Exception as e:
        print("WITHDRAW ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------
# ALL TRANSACTIONS
# ----------------------------

@app.route('/transactions', methods=['GET'])
def get_transactions():
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                t.id,
                t.account_id,
                a.name,
                t.type,
                t.amount,
                t.created_at
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            ORDER BY t.id DESC
        """)

        transactions = cursor.fetchall()
        cursor.close()
        db.close()

        for tx in transactions:
            tx['amount'] = float(tx['amount'])
            if tx.get('created_at'):
                tx['created_at'] = str(tx['created_at'])

        return jsonify(transactions)

    except Exception as e:
        print("GET TRANSACTIONS ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# ----------------------------
# ACCOUNT-WISE TRANSACTIONS
# ----------------------------

@app.route('/transactions/<int:account_id>', methods=['GET'])
def account_transactions(account_id):
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM transactions WHERE account_id=%s ORDER BY id DESC",
            (account_id,)
        )
        history = cursor.fetchall()
        cursor.close()
        db.close()

        for tx in history:
            tx['amount'] = float(tx['amount'])
            if tx.get('created_at'):
                tx['created_at'] = str(tx['created_at'])

        return jsonify(history)

    except Exception as e:
        print("ACCOUNT TRANSACTIONS ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# ----------------------------
# SERVER START
# ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)