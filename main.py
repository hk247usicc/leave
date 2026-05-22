import streamlit as st
import sqlite3
from datetime import datetime

# ------------------------
# DATABASE CONNECTION
# ------------------------
conn = sqlite3.connect("leave1.db", check_same_thread=False)
c = conn.cursor()

# USERS TABLE
c.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

# LEAVE TABLE
c.execute("""
CREATE TABLE IF NOT EXISTS leave_records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_name TEXT,
    leave_type TEXT,
    from_date TEXT,
    to_date TEXT,
    days INTEGER
)
""")

conn.commit()

# Default login
c.execute("INSERT OR IGNORE INTO users VALUES (?,?)", ("admin", "1234"))
conn.commit()

# ------------------------
# FUNCTIONS
# ------------------------
def login(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

def add_leave(name, leave_type, from_date, to_date):
    days = (to_date - from_date).days + 1
    c.execute("""INSERT INTO leave_records 
                 (staff_name, leave_type, from_date, to_date, days)
                 VALUES (?,?,?,?,?)""",
              (name, leave_type,
               from_date.strftime("%Y-%m-%d"),
               to_date.strftime("%Y-%m-%d"),
               days))
    conn.commit()

def get_records():
    c.execute("SELECT * FROM leave_records")
    return c.fetchall()

def delete_record(id):
    c.execute("DELETE FROM leave_records WHERE id=?", (id,))
    conn.commit()

def update_record(id, name, leave_type, from_date, to_date):
    days = (to_date - from_date).days + 1
    c.execute("""UPDATE leave_records 
                 SET staff_name=?, leave_type=?, from_date=?, to_date=?, days=?
                 WHERE id=?""",
              (name, leave_type,
               from_date.strftime("%Y-%m-%d"),
               to_date.strftime("%Y-%m-%d"),
               days, id))
    conn.commit()

# ------------------------
# LEAVE BALANCE CALCULATION
# ------------------------
def calculate_balance(name):
    TOTAL_CL = 8
    TOTAL_EL = 30

    c.execute("SELECT leave_type, SUM(days) FROM leave_records WHERE staff_name=? GROUP BY leave_type", (name,))
    data = c.fetchall()

    cl_used = 0
    el_used = 0

    for leave_type, total in data:
        if leave_type == "Casual Leave":
            cl_used = total if total else 0
        elif leave_type == "Earned Leave":
            el_used = total if total else 0

    return TOTAL_CL - cl_used, TOTAL_EL - el_used

# ------------------------
# LOGIN SESSION
# ------------------------
if "login" not in st.session_state:
    st.session_state.login = False

# ------------------------
# LOGIN PAGE
# ------------------------
if not st.session_state.login:
    st.title("🔐 Staff Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if login(user, pwd):
            st.session_state.login = True
            st.success("Login Successful ✅")
        else:
            st.error("Invalid Login ❌")

# ------------------------
# MAIN APP
# ------------------------
else:
    st.title("📋 Leave Management Portal")

    if st.button("Logout"):
        st.session_state.login = False
        st.rerun()

    menu = st.sidebar.selectbox("Menu", ["Apply Leave", "Leave Records", "Balance Report"])

    # ------------------------
    # APPLY LEAVE
    # ------------------------
    if menu == "Apply Leave":
        st.subheader("📌 Apply Leave")

        name = st.text_input("Staff Name")

        leave_type = st.selectbox("Leave Type", ["Casual Leave", "Earned Leave"])

        from_date = st.date_input("From Date")
        to_date = st.date_input("To Date")

        if st.button("Submit Leave"):
            if name:
                add_leave(name, leave_type, from_date, to_date)
                st.success("Leave Submitted ✅")
            else:
                st.warning("Enter Staff Name")

    # ------------------------
    # VIEW RECORDS
    # ------------------------
    elif menu == "Leave Records":
        st.subheader("📄 All Records")

        records = get_records()

        for row in records:
            id, name, leave_type, from_d, to_d, days = row

            with st.expander(f"{name} | {leave_type} | {from_d} → {to_d}"):

                st.write(f"Days: {days}")

                cl_bal, el_bal = calculate_balance(name)
                st.write(f"Balance -> CL: {cl_bal}, EL: {el_bal}")

                col1, col2 = st.columns(2)

                # DELETE
                with col1:
                    if st.button(f"Delete {id}"):
                        delete_record(id)
                        st.success("Deleted ✅")
                        st.rerun()

                # EDIT
                with col2:
                    if st.button(f"Edit {id}"):
                        st.session_state.edit_id = id

        # UPDATE FORM
        if "edit_id" in st.session_state:
            st.subheader("✏️ Update Record")

            edit_id = st.session_state.edit_id
            c.execute("SELECT * FROM leave_records WHERE id=?", (edit_id,))
            rec = c.fetchone()

            if rec:
                _, name, leave_type, from_d, to_d, _ = rec

                new_name = st.text_input("Name", value=name)
                new_type = st.selectbox("Type", ["Casual Leave", "Earned Leave"],
                                        index=0 if leave_type == "Casual Leave" else 1)

                new_from = st.date_input("From", datetime.strptime(from_d, "%Y-%m-%d"))
                new_to = st.date_input("To", datetime.strptime(to_d, "%Y-%m-%d"))

                if st.button("Update"):
                    update_record(edit_id, new_name, new_type, new_from, new_to)
                    st.success("Updated ✅")
                    del st.session_state.edit_id
                    st.rerun()

    # ------------------------
    # BALANCE REPORT
    # ------------------------
    elif menu == "Balance Report":
        st.subheader("📊 Leave Balance Report")

        records = get_records()
        staff_names = list(set([r[1] for r in records]))

        for name in staff_names:
            cl_bal, el_bal = calculate_balance(name)

            st.markdown(f"### 👤 {name}")
            st.write(f"Casual Leave Remaining: {cl_bal} / 8")
            st.write(f"Earned Leave Remaining: {el_bal} / 30")
