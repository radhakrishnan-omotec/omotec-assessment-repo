import streamlit as st
import pandas as pd
import os
import base64
import hashlib
from datetime import datetime
import logging
import sys
import urllib.parse

# Configure logging for Streamlit Cloud
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Assessment Enhancements App", layout="wide", initial_sidebar_state="expanded")

CSV_FILE = "assessment_data.csv"
DEFAULT_DATA_FILE = "EVALUATOR_INPUT.csv"
EVALUATOR_STORE = "evaluators.csv"

CSV_COLUMNS = [
    "Trainer ID", "Trainer Name", "Department", "DOJ", "Branch", "Discipline", "Course", "Date of assessment",
    "Has Knowledge of STEM (5)", "Ability to integrate STEM With related activities (10)",
    "Discusses Up-to-date information related to STEM (5)", "Provides Course Outline (5)", "Language Fluency (5)",
    "Preparation with Lesson Plan / Practicals (5)", "Time Based Activity (5)", "Student Engagement Ideas (5)",
    "Pleasing Look (5)", "Poised & Confident (5)", "Well Modulated Voice (5)", "TOTAL", "AVERAGE", "STATUS",
    "LEVEL #1", "LEVEL #2", "LEVEL #3", "Status of Score Card", "Reminder", "Evaluator Username", "Evaluator Role"
]

EVALUATOR_COLUMNS = ["username", "password_hash", "full_name", "email", "role", "created_at"]

def hash_password(password: str) -> str:
    try:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        return ""

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return hash_password(password) == stored_hash
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def load_data():
    try:
        if not os.path.exists(CSV_FILE):
            if os.path.exists(DEFAULT_DATA_FILE):
                df = pd.read_csv(DEFAULT_DATA_FILE)
            else:
                df = pd.DataFrame(columns=CSV_COLUMNS)
            df.to_csv(CSV_FILE, index=False)
        else:
            df = pd.read_csv(CSV_FILE)

        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[CSV_COLUMNS]
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        st.error("Failed to load assessment data. Please try again later.")
        return pd.DataFrame(columns=CSV_COLUMNS)

def generate_new_trainer_id():
    try:
        if os.path.exists(DEFAULT_DATA_FILE):
            df = pd.read_csv(DEFAULT_DATA_FILE)
            if "Trainer ID" in df.columns:
                existing_ids = df["Trainer ID"].dropna().astype(str)
                numbers = []
                for tid in existing_ids:
                    if tid.startswith("TR00"):
                        num_part = tid.replace("TR00", "")
                        if num_part.isdigit():
                            numbers.append(int(num_part))
                next_number = max(numbers) + 1 if numbers else 1
                return f"TR00{next_number}"
    except Exception as e:
        logger.error(f"Trainer ID generation failed: {str(e)}")
        st.warning("Failed to generate Trainer ID. Using default ID.")
    return "TR001"

def save_new_trainer_to_input(trainer_id, trainer_name, department):
    try:
        if os.path.exists(DEFAULT_DATA_FILE):
            df = pd.read_csv(DEFAULT_DATA_FILE)
        else:
            df = pd.DataFrame(columns=["Trainer ID", "Trainer Name", "Department", "Branch"])
        
        if "Trainer ID" not in df.columns:
            df["Trainer ID"] = ""
        if "Trainer Name" not in df.columns:
            df["Trainer Name"] = ""
        if "Department" not in df.columns:
            df["Department"] = ""
        if "Branch" not in df.columns:
            df["Branch"] = ""
            
        new_entry = {
            "Trainer ID": trainer_id,
            "Trainer Name": trainer_name,
            "Department": department,
            "Branch": ""
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(DEFAULT_DATA_FILE, index=False)
        return df
    except Exception as e:
        logger.error(f"Error saving new trainer: {str(e)}")
        st.error("Failed to save new trainer information.")
        return pd.DataFrame(columns=["Trainer ID", "Trainer Name", "Department", "Branch"])

def send_email_reminder(email):
    try:
        st.success(f"Reminder email sent to {email} (Simulation)")
    except Exception as e:
        logger.error(f"Error sending email reminder: {str(e)}")
        st.error("Failed to send reminder email.")

def load_evaluators():
    try:
        if not os.path.exists(EVALUATOR_STORE):
            df = pd.DataFrame(columns=EVALUATOR_COLUMNS)
            df.to_csv(EVALUATOR_STORE, index=False)
        else:
            df = pd.read_csv(EVALUATOR_STORE)
        for col in EVALUATOR_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[EVALUATOR_COLUMNS].copy()
    except Exception as e:
        logger.error(f"Error loading evaluators: {str(e)}")
        st.error("Failed to load evaluator data.")
        return pd.DataFrame(columns=EVALUATOR_COLUMNS)

def save_evaluators(df):
    try:
        df.to_csv(EVALUATOR_STORE, index=False)
    except Exception as e:
        logger.error(f"Error saving evaluators: {str(e)}")
        st.error("Failed to save evaluator data.")

def evaluator_section(df_main):
    try:
        st.subheader("🧑‍🏫 Evaluator Dashboard")

        if "logged_in" not in st.session_state or not st.session_state.get("logged_in"):
            st.warning("Please login to access the evaluator panel.")
            return

        df = df_main.copy()
        if "Trainer ID" not in df.columns:
            st.error("❌ 'Trainer ID' column missing in data.")
            return

        evaluator_role = st.selectbox("Select Evaluator Role", ["Technical Evaluator", "School Operations Evaluator"], key="evaluator_role")
        evaluator_username = st.session_state.get("logged_user", "")

        relevant_params = {
            "Technical Evaluator": [
                "Has Knowledge of STEM (5)", "Ability to integrate STEM With related activities (10)",
                "Discusses Up-to-date information related to STEM (5)", "Provides Course Outline (5)",
                "Language Fluency (5)", "Preparation with Lesson Plan / Practicals (5)"
            ],
            "School Operations Evaluator": [
                "Time Based Activity (5)", "Student Engagement Ideas (5)", "Pleasing Look (5)",
                "Poised & Confident (5)", "Well Modulated Voice (5)"
            ]
        }

        mode = st.radio("Select Trainer ID Mode", ["Enter Existing Trainer ID", "New Trainer Creation ID"])
        trainer_id = ""
        trainer_name = ""
        department = ""

        if mode.startswith("Enter"):
            try:
                if os.path.exists(DEFAULT_DATA_FILE):
                    eval_inputs_df = pd.read_csv(DEFAULT_DATA_FILE).fillna("")
                    if "Trainer ID" not in eval_inputs_df.columns:
                        st.error("❌ 'Trainer ID' column missing in EVALUATOR_INPUT.csv.")
                        return
                    available_ids = eval_inputs_df["Trainer ID"].dropna().unique().tolist()
                    if not available_ids:
                        st.warning("No Trainer IDs found in EVALUATOR_INPUT.csv.")
                        return
                    selected_id = st.selectbox("Select Existing Trainer ID", available_ids)
                    trainer_data = eval_inputs_df[eval_inputs_df["Trainer ID"] == selected_id].iloc[0].to_dict()
                    trainer_id = trainer_data.get("Trainer ID", "")
                    trainer_name = trainer_data.get("Trainer Name", "")
                    department = trainer_data.get("Department", "")
                    st.success(f"Loaded Trainer: {trainer_name} ({department})")
                else:
                    st.error("EVALUATOR_INPUT.csv not found.")
                    return
            except Exception as e:
                logger.error(f"Error loading existing trainer data: {str(e)}")
                st.error("Failed to load trainer data.")
                return

        else:
            trainer_id = st.text_input("Enter New Trainer ID (leave blank to auto-generate)")
            trainer_name = st.text_input("Trainer Name (for new ID)")
            department = st.text_input("Department (for new ID)")
            if trainer_id.strip() == "":
                if trainer_name and department:
                    try:
                        trainer_id = generate_new_trainer_id()
                        st.success(f"Auto-generated Trainer ID: {trainer_id}")
                        save_new_trainer_to_input(trainer_id, trainer_name, department)
                        st.success(f"Trainer {trainer_name} ({trainer_id}) added to existing trainers list.")
                    except Exception as e:
                        logger.error(f"Error creating new trainer: {str(e)}")
                        st.error("Failed to create new trainer.")
                else:
                    st.warning("Please enter both Trainer Name and Department to auto-generate Trainer ID.")

        past_assessments = df[df["Trainer ID"] == trainer_id] if trainer_id else pd.DataFrame()
        if not past_assessments.empty:
            st.markdown("### 🔁 Previous Assessments")
            st.dataframe(past_assessments)

        levels = ["LEVEL #1", "LEVEL #2", "LEVEL #3"]
        level_status = {}
        submissions = {}

        try:
            for level in levels:
                level_rows = past_assessments[past_assessments[level] == "QUALIFIED"]
                evaluators = level_rows["Evaluator Username"].tolist()
                has_tech = any("technical" in s.lower() for s in level_rows["Evaluator Role"].fillna(""))
                has_ops = any("school" in s.lower() for s in level_rows["Evaluator Role"].fillna(""))
                if has_tech and has_ops:
                    level_status[level] = "QUALIFIED"
                else:
                    level_status[level] = "NOT QUALIFIED"
                submissions[f"{level}_submissions"] = len(set(evaluators))
        except Exception as e:
            logger.error(f"Error processing level statuses: {str(e)}")
            st.error("Failed to process assessment levels.")

        manager_referral = ""

        for level in levels:
            with st.expander(f"🔹 {level} Assessment"):
                try:
                    if level_status.get(level) == "QUALIFIED" and submissions.get(f"{level}_submissions", 0) >= 2:
                        st.write(f"{level} already qualified by both evaluators.")
                    elif level_status.get(level) == "QUALIFIED" and submissions.get(f"{level}_submissions", 0) == 1:
                        st.write(f"{level} qualified by one evaluator. Awaiting second evaluation.")
                    else:
                        if level == "LEVEL #1" or (level == "LEVEL #2" and level_status.get("LEVEL #1") == "QUALIFIED") or \
                           (level == "LEVEL #3" and level_status.get("LEVEL #2") == "QUALIFIED"):
                            part_params = [p for p in relevant_params[evaluator_role] if any(p in col for col in df.columns)]
                            part = {k: st.text_input(k, value=past_assessments[k].iloc[0] if not past_assessments.empty else "") for k in part_params}
                            level_status_key = f"{level}_status_{evaluator_role}"
                            status = st.selectbox(f"{level} Status", ["QUALIFIED", "NOT QUALIFIED"], key=level_status_key)
                            if level == "LEVEL #3":
                                manager_referral = st.text_input("Manager Referral (Required for Level 3)")
                except Exception as e:
                    logger.error(f"Error in {level} assessment: {str(e)}")
                    st.error(f"Failed to process {level} assessment.")

        send_report_enabled = all(level_status.get(level) == "QUALIFIED" and submissions.get(f"{level}_submissions", 0) >= 2 for level in levels)
        col1, col2 = st.columns([3, 1])
        with col1:
            score_status = st.selectbox("Status of Score Card", 
                                      ["Score Cards has not been sent"] if not send_report_enabled else ["Score Cards has been sent", "Score Cards has not been sent"],
                                      key="score_status")
        with col2:
            send_score_card_disabled = score_status != "Score Cards has not been sent"
            if st.button("SEND SCORE CARD", disabled=send_score_card_disabled):
                try:
                    # Enhancement: Open default email client with pre-filled compose window
                    email_body = f"Score Card for Trainer ID: {trainer_id}\nTrainer Name: {trainer_name}\nDepartment: {department}\nStatus: {score_status}"
                    email_subject = f"Score Card for Trainer {trainer_id}"
                    mailto_link = f"mailto:?subject={urllib.parse.quote(email_subject)}&body={urllib.parse.quote(email_body)}"
                    st.markdown(f'<a href="{mailto_link}" target="_blank">Open Email Client</a>', unsafe_allow_html=True)
                    st.success(f"Score card prepared for Trainer ID: {trainer_id} (Email client opened)")
                    score_status = "Score Cards has been sent"
                    st.session_state["score_status"] = score_status
                except Exception as e:
                    logger.error(f"Error sending score card: {str(e)}")
                    st.error("Failed to prepare score card email.")

        total = st.number_input("TOTAL", min_value=0)
        avg = st.number_input("AVERAGE", min_value=0.0, step=0.1)
        status = st.selectbox("STATUS", ["CLEARED", "REDO"])
        reminder = st.text_area("Reminder")
        email = st.text_input("Evaluator Email for Reminder")
        if email:
            send_email_reminder(email)

        if st.button("💾 Submit Evaluation"):
            try:
                if not trainer_id:
                    st.error("❌ Trainer ID is required.")
                    return

                entry = {
                    "Trainer ID": trainer_id,
                    "Trainer Name": trainer_name or "New",
                    "Department": department or "",
                    "DOJ": datetime.today().date(),
                    "Branch": "", "Discipline": "", "Course": "",
                    "Date of assessment": datetime.today().date(),
                    "Evaluator Username": evaluator_username,
                    "Evaluator Role": evaluator_role,
                }

                for level in levels:
                    if level_status.get(level) != "QUALIFIED" or submissions.get(f"{level}_submissions", 0) < 2:
                        params = [p for p in relevant_params[evaluator_role] if any(p in col for col in df.columns)]
                        for param in params:
                            entry[param] = part.get(param, "")
                        entry[level] = st.session_state.get(f"{level}_status_{evaluator_role}", "NOT QUALIFIED")
                        if level == "LEVEL #3" and manager_referral:
                            entry["Manager Referral"] = manager_referral
                        break

                entry.update({
                    "TOTAL": total, "AVERAGE": avg, "STATUS": status,
                    "Status of Score Card": score_status,
                    "Reminder": reminder
                })

                # Enforce Qualification Criteria
                if entry["LEVEL #1"] == "QUALIFIED" and submissions.get("LEVEL #1_submissions", 0) >= 2:
                    courses_completed = past_assessments.shape[0]
                    if courses_completed < 10 or avg < 75.0:
                        entry["LEVEL #1"] = "NOT QUALIFIED"
                        st.warning("Level 1 requires 10 courses with at least 75% average.")
                if entry["LEVEL #2"] == "QUALIFIED" and submissions.get("LEVEL #2_submissions", 0) >= 2:
                    courses_completed = past_assessments.shape[0]
                    if courses_completed < 10 or avg < 80.0:
                        entry["LEVEL #2"] = "NOT QUALIFIED"
                        st.warning("Level 2 requires 10 courses with at least 80% average.")
                if entry["LEVEL #3"] == "QUALIFIED" and submissions.get("LEVEL #3_submissions", 0) >= 2:
                    courses_completed = past_assessments.shape[0]
                    if courses_completed < 5 or avg < 90.0 or not manager_referral:
                        entry["LEVEL #3"] = "NOT QUALIFIED"
                        st.warning("Level 3 requires 5 courses with 90% average + Manager Referral.")

                updated_df = pd.concat([df_main, pd.DataFrame([entry])], ignore_index=True)
                updated_df.to_csv(CSV_FILE, index=False)
                st.success(f"✅ Assessment Saved for Trainer ID: {trainer_id}")
            except Exception as e:
                logger.error(f"Error submitting evaluation: {str(e)}")
                st.error("Failed to submit evaluation. Please try again.")

        if st.button("Logout"):
            try:
                for key in ["logged_in", "role", "logged_user"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Logged out successfully!")
                st.rerun()
            except Exception as e:
                logger.error(f"Error during logout: {str(e)}")
                st.error("Failed to logout. Please try again.")
    except Exception as e:
        logger.error(f"Error in evaluator section: {str(e)}")
        st.error("An unexpected error occurred in the Evaluator Dashboard.")

def viewer_section(df_main):
    try:
        st.subheader("📊 Viewer Dashboard")

        if "logged_in" not in st.session_state or not st.session_state.get("logged_in"):
            st.warning("Please login to access the viewer dashboard.")
            return

        branch = st.selectbox("Select Branch", options=["", "Lokhandwala", "Juhu", "Laxmi", "Malad", "Pune", "Bangalore", "Nagpur"])
        department = st.selectbox("Select Department", options=["", "Coding", "Mechanical", "Design Thinking", "Electronics", "AI & Analytics"])

        if os.path.exists(DEFAULT_DATA_FILE):
            eval_inputs_df = pd.read_csv(DEFAULT_DATA_FILE).fillna("")
            if "Trainer ID" in eval_inputs_df.columns and "Trainer Name" in eval_inputs_df.columns and "Branch" in eval_inputs_df.columns and "Department" in eval_inputs_df.columns:
                filtered_trainers = eval_inputs_df.copy()
                if branch and department:
                    filtered_trainers = filtered_trainers[(filtered_trainers["Branch"] == branch) & (filtered_trainers["Department"] == department)]
                    if filtered_trainers.empty:
                        st.warning("No trainers for the below Branch and Department are not present in CSV file")
                        trainer_name = ""
                    else:
                        trainer_name = st.selectbox("Select Trainer Name", options=[""] + sorted(filtered_trainers["Trainer Name"].unique().tolist()))
                else:
                    trainer_name = st.selectbox("Select Trainer Name", options=[""] + sorted(eval_inputs_df["Trainer Name"].dropna().unique().tolist()))
            else:
                st.error("❌ Required columns missing in EVALUATOR_INPUT.csv.")
                trainer_name = ""
        else:
            st.error("EVALUATOR_INPUT.csv not found.")
            trainer_name = ""

        df = df_main.copy()
        if trainer_name and os.path.exists(CSV_FILE):
            trainer_id = eval_inputs_df[eval_inputs_df["Trainer Name"] == trainer_name]["Trainer ID"].iloc[0]
            trainer_report = df[df["Trainer ID"] == trainer_id]
            if not trainer_report.empty:
                st.markdown("### 📋 Assessment Records")
                st.dataframe(trainer_report, use_container_width=True)
            else:
                st.warning("No assessment records found for the selected trainer.")

        if trainer_name and not trainer_report.empty:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Download Trainer Data as CSV"):
                    try:
                        csv = trainer_report.to_csv(index=False)
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="trainer_{trainer_id}_assessment.csv">Download CSV File</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    except Exception as e:
                        logger.error(f"Error downloading CSV: {str(e)}")
                        st.error("Failed to download CSV file.")
            with col2:
                if st.button("📄 Download Trainer Data as PDF"):
                    try:
                        latex_content = r"""
                        \documentclass{article}
                        \usepackage[utf8]{inputenc}
                        \usepackage{geometry}
                        \geometry{a4paper, margin=1in}
                        \usepackage{longtable}
                        \usepackage{booktabs}
                        
                        \begin{document}
                        
                        \section*{Trainer Assessment Report}
                        \subsection*{Generated on: """ + datetime.now().strftime("%d-%m-%Y %I:%M %p IST") + r"""}
                        \subsection*{Trainer: """ + trainer_name + r""" (ID: """ + trainer_id + r""")}
                        
                        \begin{longtable}{l l l l l l}
                        \toprule
                        Date of Assessment & TOTAL & AVERAGE & STATUS & LEVEL \#1 & LEVEL \#2 \\
                        \midrule
                        """ + "".join([f"{row['Date of assessment']} & {row['TOTAL']} & {row['AVERAGE']} & {row['STATUS']} & {row['LEVEL #1']} & {row['LEVEL #2']} \\\\\n" for _, row in trainer_report.iterrows()]) + r"""
                        \bottomrule
                        \end{longtable}
                        
                        \end{document}
                        """
                        with open("trainer_report.tex", "w") as f:
                            f.write(latex_content)
                        with open("trainer_report.tex", "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                            href = f'<a href="data:application/x-latex;base64,{b64}" download="trainer_{trainer_id}_assessment.pdf">Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    except Exception as e:
                        logger.error(f"Error generating PDF: {str(e)}")
                        st.error("Failed to generate PDF report.")

        if st.button("View All Trainers"):
            try:
                if os.path.exists(DEFAULT_DATA_FILE):
                    all_trainers = eval_inputs_df[["Trainer ID", "Trainer Name"]].drop_duplicates()
                    st.markdown("### 🆔 All Trainers")
                    st.dataframe(all_trainers, use_container_width=True)
                else:
                    st.error("EVALUATOR_INPUT.csv not found.")
            except Exception as e:
                logger.error(f"Error viewing all trainers: {str(e)}")
                st.error("Failed to display trainer list.")

        if st.button("Logout"):
            try:
                for key in ["logged_in", "role", "logged_user"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Logged out successfully!")
                st.rerun()
            except Exception as e:
                logger.error(f"Error during logout: {str(e)}")
                st.error("Failed to logout. Please try again.")
    except Exception as e:
        logger.error(f"Error in viewer section: {str(e)}")
        st.error("An unexpected error occurred in the Viewer Dashboard.")

def admin_section(df_main):
    try:
        st.subheader("👨‍💼 Super Administrator Section")

        if "logged_in" not in st.session_state or not st.session_state.get("logged_in"):
            st.warning("Please login to access the admin panel.")
            return

        cols = st.columns([1, 1, 1, 1])
        if cols[0].button("Add New Evaluator"):
            st.session_state.admin_section = "add_evaluator"
        if cols[1].button("Existing Evaluators"):
            st.session_state.admin_section = "existing_evaluators"
        if cols[2].button("Edit Evaluator"):
            st.session_state.admin_section = "edit_evaluator"
        if cols[3].button("Delete Evaluator"):
            st.session_state.admin_section = "delete_evaluator"

        section = st.session_state.get("admin_section", "trainer_reports")
        evaluators_df = load_evaluators()

        if section == "add_evaluator":
            st.markdown("### 🧑‍💻 Add New Evaluator")
            with st.form("add_eval_form", clear_on_submit=True):
                new_username = st.text_input("Username", key="new_eval_user")
                new_password = st.text_input("Password", type="password", key="new_eval_pass")
                full_name = st.text_input("Full Name", key="new_eval_name")
                email = st.text_input("Email", key="new_eval_email")
                role_select = st.selectbox("Role", ["Evaluator", "Viewer", "Super Administrator"], key="new_eval_role")
                submitted = st.form_submit_button("Add Evaluator")
                if submitted:
                    try:
                        if not new_username or not new_password:
                            st.error("Username and password are required.")
                        elif new_username in evaluators_df["username"].values:
                            st.error("Username already exists.")
                        else:
                            new_entry = {
                                "username": new_username,
                                "password_hash": hash_password(new_password),
                                "full_name": full_name,
                                "email": email,
                                "role": role_select,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            evaluators_df = pd.concat([evaluators_df, pd.DataFrame([new_entry])], ignore_index=True)
                            save_evaluators(evaluators_df)
                            st.success(f"Evaluator '{new_username}' added.")
                            st.session_state.admin_section = "trainer_reports"
                    except Exception as e:
                        logger.error(f"Error adding evaluator: {str(e)}")
                        st.error("Failed to add new evaluator.")

        elif section == "existing_evaluators":
            st.markdown("### 🧑‍💻 Existing Evaluators")
            try:
                st.dataframe(evaluators_df[["username", "full_name", "email", "role", "created_at"]])
                if st.button("Back to Main"):
                    st.session_state.admin_section = "trainer_reports"
            except Exception as e:
                logger.error(f"Error displaying evaluators: {str(e)}")
                st.error("Failed to display evaluators list.")

        elif section == "edit_evaluator":
            st.markdown("### 🧑‍💻 Edit Evaluator")
            selected_eval = st.selectbox("Select Evaluator to Edit", [""] + evaluators_df["username"].tolist(), key="select_eval_edit")
            if selected_eval:
                try:
                    row = evaluators_df[evaluators_df["username"] == selected_eval].iloc[0].to_dict()
                    with st.form(f"edit_eval_form_{selected_eval}"):
                        st.markdown(f"**Username:** {row['username']} (immutable)")
                        edit_full_name = st.text_input("Full Name", value=row.get("full_name", ""), key=f"name_{selected_eval}")
                        edit_email = st.text_input("Email", value=row.get("email", ""), key=f"email_{selected_eval}")
                        edit_role = st.selectbox("Role", ["Evaluator", "Viewer", "Super Administrator"],
                                                 index=["Evaluator", "Viewer", "Super Administrator"].index(row.get("role", "Evaluator")),
                                                 key=f"role_{selected_eval}")
                        change_password = st.checkbox("Change Password", key=f"chpass_{selected_eval}")
                        new_pass = ""
                        if change_password:
                            new_pass = st.text_input("New Password", type="password", key=f"newpass_{selected_eval}")
                        edit_submitted = st.form_submit_button("Save Changes")
                        if edit_submitted:
                            idx = evaluators_df.index[evaluators_df["username"] == selected_eval][0]
                            evaluators_df.at[idx, "full_name"] = edit_full_name
                            evaluators_df.at[idx, "email"] = edit_email
                            evaluators_df.at[idx, "role"] = edit_role
                            if change_password and new_pass:
                                evaluators_df.at[idx, "password_hash"] = hash_password(new_pass)
                            save_evaluators(evaluators_df)
                            st.success(f"Evaluator '{selected_eval}' updated.")
                except Exception as e:
                    logger.error(f"Error editing evaluator: {str(e)}")
                    st.error("Failed to edit evaluator.")
            if st.button("Back to Main"):
                st.session_state.admin_section = "trainer_reports"

        elif section == "delete_evaluator":
            st.markdown("### 🧑‍💻 Delete Evaluator")
            selected_eval = st.selectbox("Select Evaluator to Delete", [""] + evaluators_df["username"].tolist(), key="select_eval_delete")
            if selected_eval:
                if st.button(f"Confirm Delete Evaluator '{selected_eval}'"):
                    try:
                        evaluators_df = evaluators_df[evaluators_df["username"] != selected_eval].reset_index(drop=True)
                        save_evaluators(evaluators_df)
                        st.warning(f"Evaluator '{selected_eval}' deleted.")
                    except Exception as e:
                        logger.error(f"Error deleting evaluator: {str(e)}")
                        st.error("Failed to delete evaluator.")
            if st.button("Back to Main"):
                st.session_state.admin_section = "trainer_reports"

        else:
            st.markdown("---")
            st.markdown("### 📋 Trainer Reports Overview")

            trainer_filter = st.text_input("Filter by Trainer Name or ID", "")
            filtered = df_main.copy()
            if trainer_filter:
                try:
                    mask = filtered["Trainer ID"].astype(str).str.contains(trainer_filter, case=False, na=False) | \
                           filtered["Trainer Name"].astype(str).str.contains(trainer_filter, case=False, na=False)
                    filtered = filtered[mask]
                except Exception as e:
                    logger.error(f"Error filtering trainers: {str(e)}")
                    st.error("Failed to apply trainer filter.")

            st.markdown("#### Matching Trainer Assessments")
            st.dataframe(filtered)

            trainer_ids = sorted(filtered["Trainer ID"].dropna().unique().tolist())
            selected_trainer = st.selectbox("Select Trainer for Detailed Report", [""] + trainer_ids)
            if selected_trainer:
                trainer_reports = df_main[df_main["Trainer ID"] == selected_trainer]
                st.markdown(f"##### Reports for Trainer ID: {selected_trainer}")
                st.dataframe(trainer_reports)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        label="Download Trainer Report CSV",
                        data=trainer_reports.to_csv(index=False),
                        file_name=f"trainer_{selected_trainer}_reports.csv"
                    )
                with col2:
                    st.download_button(
                        label="Download All Filtered Reports CSV",
                        data=filtered.to_csv(index=False),
                        file_name="filtered_trainer_reports.csv"
                    )
                with col3:
                    if st.button("Download Evaluators/Trainers PDF"):
                        try:
                            latex_content = r"""
                            \documentclass{article}
                            \usepackage[utf8]{inputenc}
                            \usepackage{geometry}
                            \geometry{a4paper, margin=1in}
                            \usepackage{longtable}
                            \usepackage{booktabs}

                            \begin{document}

                            \section*{Evaluator and Trainer Report}
                            \subsection*{Generated on: """ + datetime.now().strftime("%d-%m-%Y %I:%M %p IST") + r"""}
                            \subsubsection*{Evaluators}
                            \begin{longtable}{l l l l l}
                            \toprule
                            Username & Full Name & Email & Role & Created At \\
                            \midrule
                            """ + "".join([f"{row['username']} & {row['full_name']} & {row['email']} & {row['role']} & {row['created_at']} \\\\\n" for _, row in evaluators_df.iterrows()]) + r"""
                            \bottomrule
                            \end{longtable}

                            \subsubsection*{Trainers}
                            \begin{longtable}{l l l l}
                            \toprule
                            Trainer ID & Trainer Name & Branch & Department \\
                            \midrule
                            """ + ("" if not os.path.exists(DEFAULT_DATA_FILE) else "".join([f"{row['Trainer ID']} & {row['Trainer Name']} & {row['Branch']} & {row['Department']} \\\\\n" for _, row in pd.read_csv(DEFAULT_DATA_FILE).iterrows()])) + r"""
                            \bottomrule
                            \end{longtable}

                            \end{document}
                            """
                            with open("report.tex", "w") as f:
                                f.write(latex_content)
                            with open("report.tex", "rb") as f:
                                b64 = base64.b64encode(f.read()).decode()
                                href = f'<a href="data:application/x-latex;base64,{b64}" download="evaluators_trainers_report.pdf">Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        except Exception as e:
                            logger.error(f"Error generating PDF report: {str(e)}")
                            st.error("Failed to generate PDF report.")

        if st.button("Logout"):
            try:
                for key in ["logged_in", "role", "logged_user"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Logged out successfully!")
                st.rerun()
            except Exception as e:
                logger.error(f"Error during logout: {str(e)}")
                st.error("Failed to logout. Please try again.")
    except Exception as e:
        logger.error(f"Error in admin section: {str(e)}")
        st.error("An unexpected error occurred in the Admin Dashboard.")

def set_background(image_file):
    try:
        with open(image_file, "rb") as image:
            img_bytes = base64.b64encode(image.read()).decode()
        page_bg_img = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{img_bytes}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error setting background: {str(e)}")
        st.warning("Failed to set background image.")

def login_ui():
    try:
        st.sidebar.title("🔐 Login Panel")

        role = st.radio("Select Role", ["Viewer", "Evaluator", "Super_Administrator"])
        bg_image = f"background{'' if role == 'Viewer' else '1' if role == 'Evaluator' else '2'}.jpg"
        if os.path.exists(bg_image):
            set_background(bg_image)

        col1, col2 = st.columns([4, 1])

        with col1:
            st.title("🧑‍💼 Assessment Login Form")
            username = st.text_input("Username", key="username_input")
            password = st.text_input("Password", type="password", key="password_input")
            login_btn = st.button("🔓 Login")

            if login_btn:
                try:
                    if (role == "Viewer" and username == "omotec" and password == "omotec") or \
                       (role == "Evaluator" and username == "omotec1" and password == "omotec123") or \
                       (role == "Super_Administrator" and username == "omotec2" and password == "omotec@123#"):
                        st.session_state.logged_in = True
                        st.session_state["role"] = role.replace("_", " ")
                        st.session_state["logged_user"] = username
                        st.success(f"✅ Logged in successfully as {role.replace('_', ' ')}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Login Credentials")
                except Exception as e:
                    logger.error(f"Error during login: {str(e)}")
                    st.error("Failed to process login. Please try again.")

        with col2:
            if os.path.exists("NEW LOGO - OMOTEC.png"):
                st.image("NEW LOGO - OMOTEC.png", use_column_width=True)
    except Exception as e:
        logger.error(f"Error in login UI: {str(e)}")
        st.error("An unexpected error occurred in the Login Panel.")

def main():
    try:
        if "logged_in" not in st.session_state or not st.session_state.get("logged_in"):
            login_ui()
        else:
            df_main = load_data()
            role = st.session_state.get("role", "")
            if role == "Evaluator":
                evaluator_section(df_main)
            elif role == "Viewer":
                viewer_section(df_main)
            elif role == "Super Administrator":
                admin_section(df_main)
            else:
                st.warning("Invalid role. Please login with a valid role.")
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        st.error("An unexpected error occurred in the application.")

if __name__ == "__main__":
    main()