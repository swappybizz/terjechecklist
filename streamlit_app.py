import streamlit as st
from pymongo import MongoClient
import fitz  # PyMuPDF
import docx
from datetime import datetime
st.set_page_config(page_title="Sjekkliste", page_icon=":clipboard:")

MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client['Stig_checklist']
collection = db['checklist']

client_submissions = db['client_submissions']

st.title("Din Sjekkliste Opplastingsapp")

# Functions to read different file types
def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def read_docx(file):
    doc = docx.Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text

def read_txt(file):
    text = file.read().decode("utf-8")
    return text

# Upload file in sidebar
uploaded_file = st.sidebar.file_uploader("Velg en fil", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1]
    if file_type == "pdf":
        content = read_pdf(uploaded_file)
    elif file_type == "docx":
        content = read_docx(uploaded_file)
    elif file_type == "txt":
        content = read_txt(uploaded_file)
    else:
        content = "Ikke støttet filtype."
    
    # Save checklist to the database
    checklist = {
        "filnavn": uploaded_file.name,
        "innhold": content,
        "opplastingsdato": datetime.now(),
        "tildelte_klienter": []
    }
    
    # insert only if the checklist is not already in the database
    if not collection.find_one({"filnavn": uploaded_file.name}):
        collection.insert_one(checklist)
    else:
        st.warning("Sjekkliste med dette navnet er allerede lastet opp.")

# Sidebar to display uploaded checklists
st.sidebar.title("Opplastede Sjekklister")
checklists = list(collection.find().sort("opplastingsdato", -1))

if checklists:
    checklist_titles = [checklist["filnavn"] for checklist in checklists]
    selected_checklist = st.sidebar.radio("Velg en sjekkliste", checklist_titles)

    selected_content = None
    assigned_clients = []
    checklist_id = None
    for checklist in checklists:
        if checklist["filnavn"] == selected_checklist:
            selected_content = checklist["innhold"]
            assigned_clients = checklist.get("tildelte_klienter", [])
            checklist_id = checklist["_id"]
            break

    if selected_content:
        st.text_area("Fil Innhold", selected_content, height=500)
        
        # Display assigned clients
        st.write("Tildelte Klienter:", ", ".join(assigned_clients) if assigned_clients else "Ingen")

        # Input to assign checklist
        new_client_key = st.text_input("Tildel Sjekkliste til Klient (Skriv inn Klientnøkkel)",)
        if st.button("Tildel"):
            if new_client_key:
                collection.update_one(
                    {"_id": checklist_id},
                    {"$addToSet": {"tildelte_klienter": new_client_key}}
                )
                st.success(f"Sjekkliste tildelt {new_client_key}")
            else:
                st.error("Klientnøkkel kan ikke være tom.")

else:
    st.text("Ingen sjekklister lastet opp.")
    
    
for client_submission in client_submissions.find():
    with st.expander(f"Klientinnlevering: {client_submission['client_id']} {client_submission['current_date']}",expanded=False):
        st.code(client_submission['submission'])
