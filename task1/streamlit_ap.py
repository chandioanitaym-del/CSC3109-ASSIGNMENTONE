import pandas as pd
import requests
import streamlit as st

API = "http://127.0.0.1:5000"

st.set_page_config(page_title="Student Management", page_icon="🎓", layout="wide")
st.title("🎓 Student Management")


def api(method, path, **kwargs):
    """Call the Flask API. Returns (data, error_message)."""
    try:
        r = requests.request(method, f"{API}{path}", timeout=5, **kwargs)
    except requests.RequestException:
        return None, "Cannot reach the Flask API. Is app.py running on port 5000?"
    data = r.json() if r.content else {}
    if not r.ok:
        return None, data.get("error", f"Request failed ({r.status_code})")
    return data, None


def done(message):
    """Remember a success message, then rerun so the table refreshes."""
    st.session_state["flash"] = message
    st.rerun()


if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

students, error = api("GET", "/students")
if error:
    st.error(error)
    st.stop()

# ---- All students -------------------------------------------------------
st.subheader("All students")
if students:
    df = pd.DataFrame(students).rename(
        columns={"id": "ID", "name": "Name", "department": "Department", "email": "Email"}
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No students yet. Add one below.")

add_tab, update_tab, delete_tab = st.tabs(["➕ Add", "✏️ Update", "🗑️ Delete"])

# ---- Add ----------------------------------------------------------------
with add_tab:
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Name")
        dept = st.text_input("Department")
        email = st.text_input("Email")
        if st.form_submit_button("Add student"):
            _, err = api("POST", "/students", json={"name": name, "department": dept, "email": email})
            if err:
                st.error(err)
            else:
                done("Student added.")

# ---- Update -------------------------------------------------------------
with update_tab:
    if not students:
        st.info("Nothing to update.")
    else:
        by_id = {s["id"]: s for s in students}
        sid = st.selectbox(
            "Select student",
            list(by_id),
            format_func=lambda i: f"#{i} - {by_id[i]['name']}",
            key="update_select",
        )
        cur = by_id[sid]
        with st.form(f"update_form_{sid}"):
            name = st.text_input("Name", cur["name"])
            dept = st.text_input("Department", cur["department"])
            email = st.text_input("Email", cur["email"])
            if st.form_submit_button("Save changes"):
                _, err = api("PUT", f"/students/{sid}", json={"name": name, "department": dept, "email": email})
                if err:
                    st.error(err)
                else:
                    done("Student updated.")

# ---- Delete -------------------------------------------------------------
with delete_tab:
    if not students:
        st.info("Nothing to delete.")
    else:
        by_id = {s["id"]: s for s in students}
        sid = st.selectbox(
            "Select student",
            list(by_id),
            format_func=lambda i: f"#{i} - {by_id[i]['name']}",
            key="delete_select",
        )
        if st.button("Delete student", type="primary"):
            _, err = api("DELETE", f"/students/{sid}")
            if err:
                st.error(err)
            else:
                done("Student deleted.")
