"""Streamlit Dashboard for DPR Monitoring Agent."""

import os
import time

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


st.set_page_config(
    page_title="DPR Monitoring Agent",
    page_icon="🏛️",
    layout="wide",
)


def fetch_documents():
    """Fetch list of processed documents."""
    try:
        res = requests.get(f"{BACKEND_URL}/documents")
        res.raise_for_status()
        return res.json().get("documents", [])
    except Exception as e:
        st.error(f"Failed to fetch documents: {e}")
        return []


def upload_document(uploaded_file):
    """Upload PDF and extract issues."""
    with st.spinner("Uploading and analyzing document... This may take a minute."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            upload_res = requests.post(f"{BACKEND_URL}/upload", files=files)
            upload_res.raise_for_status()
            doc_id = upload_res.json()["id"]

            st.info(f"Document uploaded (ID: {doc_id}). Extracting issues...")

            # Extract (this takes time as it calls Ollama)
            extract_res = requests.post(
                f"{BACKEND_URL}/extract/{doc_id}",
                json={"deduplicate": True, "classify_akd": True}
            )
            extract_res.raise_for_status()
            return doc_id
        except Exception as e:
            st.error(f"Processing failed: {e}")
            return None


def fetch_document_details(doc_id):
    """Fetch details for a single document."""
    try:
        res = requests.get(f"{BACKEND_URL}/documents/{doc_id}")
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Failed to fetch document details: {e}")
        return None


def save_edited_issues(doc_id, edited_df):
    """Send edited issues back to backend."""
    try:
        # Convert df back to list of dicts
        issues_list = edited_df.to_dict("records")
        # Ensure lists are lists, handle pandas stringifying them
        for item in issues_list:
            if isinstance(item.get("sections"), str):
                item["sections"] = [s.strip() for s in item["sections"].split(",")]
            if isinstance(item.get("source_pages"), str):
                item["source_pages"] = [int(p.strip()) for p in item["source_pages"].split(",")]
            if isinstance(item.get("review_flags"), str):
                item["review_flags"] = [f.strip() for f in item["review_flags"].split(",") if f.strip()]
        
        res = requests.put(f"{BACKEND_URL}/documents/{doc_id}/issues", json=issues_list)
        res.raise_for_status()
        st.toast("Edits saved successfully!", icon="✅")
    except Exception as e:
        st.error(f"Failed to save edits: {e}")


def main():
    st.title("🏛️ DPR Executive Summary Analyzer")

    # Sidebar: Document Selection
    st.sidebar.header("Documents")
    docs = fetch_documents()
    
    doc_options = {"New Upload": None}
    for d in docs:
        label = f"{d['filename']} ({d['created_at'][:10]})"
        doc_options[label] = d["id"]

    selected_label = st.sidebar.radio("Select Document", list(doc_options.keys()))
    selected_doc_id = doc_options[selected_label]

    if selected_doc_id is None:
        st.subheader("Upload New Document")
        uploaded_file = st.file_uploader("Upload Executive Summary PDF", type="pdf")
        if uploaded_file is not None:
            if st.button("Process Document", type="primary"):
                new_doc_id = upload_document(uploaded_file)
                if new_doc_id:
                    st.success("Processing complete!")
                    st.rerun()
    else:
        doc = fetch_document_details(selected_doc_id)
        if not doc:
            return

        st.subheader(f"Results: {doc['filename']}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pages", doc['total_pages'])
        col2.metric("Sections", len(doc['sections']))
        col3.metric("Issues Found", len(doc['issues']))
        col4.metric("Flagged Issues", sum(1 for i in doc['issues'] if i.get('review_flags')))

        st.divider()

        # Display and Edit Issues
        if doc['issues']:
            st.write("### Extracted Issues")
            st.caption("Review the extracted issues below. You can edit the AKD or Title directly in the table if needed. Rows with warnings are highlighted.")

            # Convert to DataFrame for editing
            df = pd.DataFrame(doc['issues'])
            
            # Formatting for display
            df["sections"] = df["sections"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
            df["source_pages"] = df["source_pages"].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)
            df["review_flags"] = df["review_flags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

            # Reorder columns
            cols = ["title", "akd", "date", "description", "review_flags", "confidence", "akd_confidence", "sections", "source_pages"]
            df = df[cols]

            # Style function
            def highlight_flags(row):
                if row['review_flags']:
                    return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
                return [''] * len(row)

            # Display Data Editor
            edited_df = st.data_editor(
                df.style.apply(highlight_flags, axis=1),
                column_config={
                    "title": st.column_config.TextColumn("Issue Title"),
                    "akd": st.column_config.TextColumn("Assigned AKD"),
                    "date": "Date",
                    "description": "Description",
                    "review_flags": st.column_config.TextColumn("Warnings", disabled=True),
                    "confidence": st.column_config.NumberColumn("Extract Conf.", format="%.2f", disabled=True),
                    "akd_confidence": st.column_config.NumberColumn("AKD Conf.", format="%.2f", disabled=True),
                    "sections": st.column_config.TextColumn("Sections", disabled=True),
                    "source_pages": st.column_config.TextColumn("Pages", disabled=True),
                },
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
            )

            # Save Edits
            if st.button("💾 Save Edits"):
                save_edited_issues(selected_doc_id, edited_df)

            st.divider()

            # Exports
            st.write("### Generate Reports")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                excel_url = f"{BACKEND_URL}/documents/{selected_doc_id}/export/excel"
                excel_res = requests.get(excel_url)
                if excel_res.status_code == 200:
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=excel_res.content,
                        file_name=f"{doc['filename']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            
            with col_b:
                word_url = f"{BACKEND_URL}/documents/{selected_doc_id}/export/word"
                word_res = requests.get(word_url)
                if word_res.status_code == 200:
                    st.download_button(
                        label="📥 Download Word Report",
                        data=word_res.content,
                        file_name=f"{doc['filename']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                    
            with col_c:
                json_url = f"{BACKEND_URL}/documents/{selected_doc_id}/export/json"
                json_res = requests.get(json_url)
                if json_res.status_code == 200:
                    st.download_button(
                        label="📥 Download Raw JSON",
                        data=json_res.content,
                        file_name=f"{doc['filename']}.json",
                        mime="application/json",
                    )
        else:
            st.info("No issues found in this document.")


if __name__ == "__main__":
    main()
