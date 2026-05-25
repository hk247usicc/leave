import streamlit as st
import sqlite3
from datetime import datetime

# -----------------------------
# DATABASE
# -----------------------------
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
    leave_days REAL,
    from_date TEXT,
    to_date TEXT
)
""")

conn.commit()

# Default user
c.execute("INSERT OR IGNORE INTO users VALUES (?,?)", ("admin", "1234"))
conn.commit()

# -----------------------------
# FUNCTIONS
# -----------------------------
def login(u, p):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
    return c.fetchone()

def add_leave(name, ltype, days, f, t):
    c.execute("""INSERT INTO leave_records
                (staff_name, leave_type, leave_days, from_date, to_date)
                VALUES(?,?,?,?,?)""",
              (name, ltype, days,
               f.strftime("%Y-%m-%d"),
               t.strftime("%Y-%m-%d")))
    conn.commit()

def get_all():
    c.execute("SELECT * FROM leave_records")
    return c.fetchall()

def delete_record(i):
    c.execute("DELETE FROM leave_records WHERE id=?", (i,))
    conn.commit()

def update_record(i, name, ltype, days, f, t):
    c.execute("""UPDATE leave_records SET
                staff_name=?, leave_type=?, leave_days=?,
                from_date=?, to_date=? WHERE id=?""",
              (name, ltype, days,
               f.strftime("%Y-%m-%d"),
               t.strftime("%Y-%m-%d"), i))
    conn.commit()

# -----------------------------
# BALANCE FUNCTION
# -----------------------------
def get_balance(name):
    TOTAL_CL = 8
    TOTAL_EL = 30

    c.execute("SELECT leave_type, SUM(leave_days) FROM leave_records WHERE staff_name=? GROUP BY leave_type", (name,))
    data = c.fetchall()

    cl_used = 0
    el_used = 0

    for t, d in data:
        if t in ["CL", "HALF CL"]:
            cl_used += d if d else 0
        elif t in ["EL", "HALF EL"]:
            el_used += d if d else 0

    return TOTAL_CL - cl_used, TOTAL_EL - el_used

# -----------------------------
# LOGIN STATE
# -----------------------------
if "login" not in st.session_state:
    st.session_state.login = False


# -----------------------------
# LOGIN PAGE
# -----------------------------
if not st.session_state.login:

    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if login(u, p):
            st.session_state.login = True
            st.success("Login successful ✅")
        else:
            st.error("Invalid ❌")

# -----------------------------
# MAIN APP
# -----------------------------
else:

    st.title("📋 Leave Management System")

    if st.button("Logout"):
        st.session_state.login = False
        st.rerun()

    menu = st.sidebar.selectbox("Menu", ["Apply Leave", "Records", "Balance Report"])

    # -------------------------
    # APPLY LEAVE
    # -------------------------
    if menu == "Apply Leave":

        st.subheader("📌 Apply Leave")

        name = st.text_input("Staff Name")

        leave_type = st.selectbox("Leave Type",
                                 ["CL", "EL", "HALF CL", "HALF EL"])

        from_date = st.date_input("From Date")
        to_date = st.date_input("To Date")

        days = (to_date - from_date).days + 1

        # Assign leave values
        if leave_type == "CL":
            leave_days = days
        elif leave_type == "EL":
            leave_days = days
        elif leave_type == "HALF CL":
            leave_days = 0.5 * days
        elif leave_type == "HALF EL":
            leave_days = 0.5 * days

        if st.button("Submit"):
            if name:
                add_leave(name, leave_type, leave_days, from_date, to_date)
                st.success("Leave Added ✅")
            else:
                st.warning("Enter Name")

    # -------------------------
    # RECORDS
    # -------------------------
    elif menu == "Records":

        st.subheader("📄 All Records")

        for r in get_all():
            id, name, ltype, days, f, t = r

            with st.expander(f"{name} | {ltype} | {f} → {t}"):

                st.write(f"Days Used: {days}")

                cl_bal, el_bal = get_balance(name)
                st.write(f"Balance → CL: {cl_bal}, EL: {el_bal}")

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

        # UPDATE
        if "edit_id" in st.session_state:

            st.subheader("✏ Update Record")

            edit_id = st.session_state.edit_id

            c.execute("SELECT * FROM leave_records WHERE id=?", (edit_id,))
            rec = c.fetchone()

            if rec:
                _, name, ltype, days, f, t = rec

                new_name = st.text_input("Name", value=name)
                new_type = st.selectbox("Type",
                                        ["CL", "EL", "HALF CL", "HALF EL"],
                                        index=["CL","EL","HALF CL","HALF EL"].index(ltype))

                new_from = st.date_input("From", datetime.strptime(f, "%Y-%m-%d"))
                new_to = st.date_input("To", datetime.strptime(t, "%Y-%m-%d"))

                new_days = (new_to - new_from).days + 1

                if new_type in ["HALF CL", "HALF EL"]:
                    new_days = new_days * 0.5

                if st.button("Update"):

                    update_record(edit_id, new_name, new_type, new_days, new_from, new_to)
                    st.success("Updated ✅")
                    del st.session_state.edit_id
                    st.rerun()

    # -------------------------
    # BALANCE REPORT
    # -------------------------
    elif menu == "Balance Report":

        st.subheader("📊 Leave Balance Report")

        names = list(set([r[1] for r in get_all()]))

        for n in names:
            cl_bal, el_bal = get_balance(n)

            st.markdown(f"### 👤 {n}")
            st.write(f"Casual Leave Remaining: {cl_bal} / 8")
            st.write(f"Earned Leave Remaining: {el_bal} / 30")