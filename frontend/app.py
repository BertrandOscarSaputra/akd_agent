"""Streamlit Dashboard for DPR Monitoring Agent."""

import os

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 300  # 5 minute timeout for long operations


st.set_page_config(
    page_title="DPR Monitoring Agent",
    page_icon="🏛️",
    layout="wide",
)


# Session state initialization
if "selected_doc_id" not in st.session_state:
    st.session_state.selected_doc_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False


def fetch_documents():
    """Fetch list of processed documents."""
    try:
        res = requests.get(f"{BACKEND_URL}/documents", timeout=10)
        res.raise_for_status()
        return res.json().get("documents", [])
    except Exception as e:
        st.error(f"Failed to fetch documents: {e}")
        return []


def upload_and_extract(uploaded_file, progress_bar, status_text):
    """Upload PDF and extract issues with progress feedback."""
    try:
        # Step 1: Upload
        status_text.text("📤 Uploading document...")
        progress_bar.progress(10)
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        upload_res = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
        upload_res.raise_for_status()
        upload_data = upload_res.json()
        doc_id = upload_data["id"]
        sections_found = upload_data.get("sections_found", 0)

        # Step 2: Extract
        status_text.text(f"🤖 Extracting issues from {sections_found} sections... (this takes a while)")
        progress_bar.progress(30)
        extract_res = requests.post(
            f"{BACKEND_URL}/extract/{doc_id}",
            json={"deduplicate": True, "classify_akd": True},
            timeout=REQUEST_TIMEOUT,
        )
        extract_res.raise_for_status()
        extract_data = extract_res.json()

        progress_bar.progress(100)
        status_text.text(
            f"✅ Done! Extracted {extract_data['total_issues']} issues "
            f"in {extract_data['extraction_duration_ms'] / 1000:.1f}s"
        )
        return doc_id

    except requests.exceptions.Timeout:
        st.error("⏱️ Processing timed out. The model may be too slow. Try again or use a smaller model.")
        return None
    except Exception as e:
        st.error(f"Processing failed: {e}")
        return None


def fetch_document_details(doc_id):
    """Fetch details for a single document."""
    try:
        res = requests.get(f"{BACKEND_URL}/documents/{doc_id}", timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Failed to fetch document details: {e}")
        return None


def save_edited_issues(doc_id, edited_df):
    """Send edited issues back to backend."""
    try:
        issues_list = edited_df.to_dict("records")
        for item in issues_list:
            if isinstance(item.get("sections"), str):
                item["sections"] = [s.strip() for s in item["sections"].split(",")]
            if isinstance(item.get("source_pages"), str):
                item["source_pages"] = [int(p.strip()) for p in item["source_pages"].split(",")]
            if isinstance(item.get("review_flags"), str):
                item["review_flags"] = [f.strip() for f in item["review_flags"].split(",") if f.strip()]

        res = requests.put(f"{BACKEND_URL}/documents/{doc_id}/issues", json=issues_list, timeout=10)
        res.raise_for_status()
        st.toast("Edits saved successfully!", icon="✅")
    except Exception as e:
        st.error(f"Failed to save edits: {e}")


def render_upload_page():
    """Render the upload page."""
    st.subheader("Upload New Document")
    uploaded_file = st.file_uploader("Upload Executive Summary PDF", type="pdf")

    if uploaded_file is not None:
        col_process, col_cancel = st.columns([1, 1])
        with col_process:
            process_clicked = st.button("▶️ Process Document", type="primary", use_container_width=True)
        with col_cancel:
            # Placeholder for stop — Streamlit will just stop on page nav
            pass

        if process_clicked:
            progress_bar = st.progress(0)
            status_text = st.empty()

            new_doc_id = upload_and_extract(uploaded_file, progress_bar, status_text)
            if new_doc_id:
                st.session_state.selected_doc_id = new_doc_id
                st.balloons()
                st.rerun()


def render_document_page(doc_id):
    """Render the document details page."""
    doc = fetch_document_details(doc_id)
    if not doc:
        return

    st.subheader(f"📄 Results: {doc['filename']}")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pages", doc["total_pages"])
    col2.metric("Sections", len(doc["sections"]))
    col3.metric("Issues Found", len(doc["issues"]))
    flagged = sum(1 for i in doc["issues"] if i.get("review_flags"))
    col4.metric("⚠️ Flagged", flagged)

    st.divider()

    if not doc["issues"]:
        st.info("No issues found in this document. The PDF may not contain recognizable sections.")
        return

    st.write("### Extracted Issues")
    st.caption("Edit the AKD or Title directly in the table. Rows with warnings are highlighted in red.")

    # Build DataFrame
    df = pd.DataFrame(doc["issues"])
    df["sections"] = df["sections"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    df["source_pages"] = df["source_pages"].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)
    df["review_flags"] = df["review_flags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

    cols = ["title", "akd", "date", "description", "review_flags", "confidence", "akd_confidence", "sections", "source_pages"]
    available_cols = [c for c in cols if c in df.columns]
    df = df[available_cols]

    # Style
    def highlight_flags(row):
        if row.get("review_flags", ""):
            return ["background-color: rgba(255, 0, 0, 0.1)"] * len(row)
        return [""] * len(row)

    edited_df = st.data_editor(
        df.style.apply(highlight_flags, axis=1),
        column_config={
            "title": st.column_config.TextColumn("Issue Title", width="large"),
            "akd": st.column_config.TextColumn("Assigned AKD"),
            "date": "Date",
            "description": st.column_config.TextColumn("Description", width="large"),
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

    if st.button("💾 Save Edits", type="primary"):
        save_edited_issues(doc_id, edited_df)

    st.divider()

    # Exports
    st.write("### 📥 Download Reports")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("Generate Excel", use_container_width=True):
            with st.spinner("Generating..."):
                res = requests.get(f"{BACKEND_URL}/documents/{doc_id}/export/excel", timeout=30)
                if res.status_code == 200:
                    st.download_button(
                        label="📥 Download Excel",
                        data=res.content,
                        file_name=f"{doc['filename']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

    with col_b:
        if st.button("Generate Word", use_container_width=True):
            with st.spinner("Generating..."):
                res = requests.get(f"{BACKEND_URL}/documents/{doc_id}/export/word", timeout=30)
                if res.status_code == 200:
                    st.download_button(
                        label="📥 Download Word",
                        data=res.content,
                        file_name=f"{doc['filename']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

    with col_c:
        if st.button("Generate JSON", use_container_width=True):
            with st.spinner("Generating..."):
                res = requests.get(f"{BACKEND_URL}/documents/{doc_id}/export/json", timeout=30)
                if res.status_code == 200:
                    st.download_button(
                        label="📥 Download JSON",
                        data=res.content,
                        file_name=f"{doc['filename']}.json",
                        mime="application/json",
                    )


def main():
    st.title("🏛️ DPR Executive Summary Analyzer")

    # Sidebar: Document list
    st.sidebar.header("📁 Documents")
    docs = fetch_documents()

    # Build options — put "New Upload" first
    doc_options = {"➕ New Upload": None}
    for d in docs:
        has_issues = d.get("sections_found", 0) > 0
        icon = "✅" if has_issues else "📄"
        label = f"{icon} {d['filename']} ({d['created_at'][:10]})"
        doc_options[label] = d["id"]

    # If we just finished processing, default to that document
    default_index = 0
    if st.session_state.selected_doc_id:
        for idx, (label, doc_id) in enumerate(doc_options.items()):
            if doc_id == st.session_state.selected_doc_id:
                default_index = idx
                break

    selected_label = st.sidebar.radio(
        "Select Document",
        list(doc_options.keys()),
        index=default_index,
    )
    selected_doc_id = doc_options[selected_label]

    # Update session state
    st.session_state.selected_doc_id = selected_doc_id

    if selected_doc_id is None:
        render_upload_page()
    else:
        render_document_page(selected_doc_id)


if __name__ == "__main__":
    main()
