import streamlit as st
import PyPDF2
import re
import io

# ------------------------------------------------------------
# Streamlit setup
# ------------------------------------------------------------
st.set_page_config(page_title="Smart Credit Card Parser", page_icon="💳", layout="centered")
st.title("💳 Multi-Format Credit Card Statement Parser")
st.caption("Upload any credit card statement (ICICI, HDFC, SBI, Axis, Amex, or generic)")

uploaded_file = st.file_uploader("📂 Upload PDF", type=["pdf"])

# ------------------------------------------------------------
# PDF text extraction
# ------------------------------------------------------------
def extract_text_from_pdf(uploaded_file):
    text = ""
    reader = PyPDF2.PdfReader(uploaded_file)
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"
    return text


# ------------------------------------------------------------
# Utility: clean text
# ------------------------------------------------------------
def normalize_text(raw):
    text = re.sub(r"\s+", " ", raw)
    text = text.replace("–", "-")
    return text.strip()


# ------------------------------------------------------------
# Extraction logic
# ------------------------------------------------------------
def extract_statement_data(text):
    data = {}
    t = normalize_text(text)

    # --- Bank Detection ---
    bank = re.search(
        r"(ICICI|HDFC|AXIS|SBI|AMERICAN\s*EXPRESS|CITI|KOTAK|XXX\s*BANK)",
        t, re.IGNORECASE)
    data["Bank Name"] = bank.group(1).upper() if bank else "Not Found"

    # --- Customer Name ---
    name = re.search(
        r"(?:Customer\s*Name|Name\s*on\s*Card|Cardholder\s*Name|Account\s*Name)[:\s]*([A-Z][A-Z\s\.]+)",
        t, re.IGNORECASE)
    if not name:
        name = re.search(r"\b(MR|MS|MRS)\s+[A-Z]+\s+[A-Z]+\s*[A-Z]*", t)
    data["Customer Name"] = name.group(1).strip() if name else "Not Found"

    # --- Account / Card Number ---
    card = re.search(r"(\d{4}\s?X{2,4}\s?X{2,4}\s?\d{3,4})", t)
    if not card:
        card = re.search(r"Account\s*Number[:\s-]*([0-9\-Xx\s]+)", t)
    data["Card Number"] = card.group(1).strip() if card else "Not Found"

    # --- Statement / Billing Period ---
    period = re.search(
        r"(Statement\s*Period|Billing\s*Cycle|Opening\/Closing\s*Date)[^0-9]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}).*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        t, re.IGNORECASE)
    if period:
        data["Statement Period"] = f"{period.group(2)} TO {period.group(3)}"
    else:
        date = re.search(
            r"(Statement\s*Date|Bill\s*Date|Date)[:\s-]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            t, re.IGNORECASE)
        data["Statement Period"] = date.group(2) if date else "Not Found"

    # --- Payment Due Date ---
    due = re.search(
        r"(Payment\s*Due\s*Date|Due\s*Date|Pay\s*By)[:\s-]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|[A-Z][a-z]+\s*\d{1,2},?\s*\d{2,4})",
        t, re.IGNORECASE)
    data["Payment Due Date"] = due.group(2) if due else "Not Found"

    # --- Total / New Balance ---
    total_due = re.search(
        r"(Total\s*Amount\s*Due|New\s*Balance|Payment\s*Due|Balance\s*Due)[^\d₹$]*([₹$]?\s?[\d,]+\.\d{2})",
        t, re.IGNORECASE)
    data["Total / New Balance"] = total_due.group(2).replace(" ", "") if total_due else "Not Found"

    # --- Minimum Payment ---
    min_pay = re.search(
        r"(Minimum\s*Payment\s*Due|Minimum\s*Amount\s*Due)[^\d₹$]*([₹$]?\s?[\d,]+\.\d{2})",
        t, re.IGNORECASE)
    data["Minimum Payment Due"] = min_pay.group(2).replace(" ", "") if min_pay else "Not Found"

    # --- Credit Limit (if available) ---
    limit = re.search(r"(Credit\s*(Access\s*)?Line|Credit\s*Limit)[:\s$₹]*([\d,]+\.\d{2})", t, re.IGNORECASE)
    data["Credit Limit"] = limit.group(3) if limit else "Not Found"

    return data


# ------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------
if uploaded_file:
    try:
        text = extract_text_from_pdf(uploaded_file)
        fields = extract_statement_data(text)

        st.subheader("📊 Extracted Details")
        for key, value in fields.items():
            st.write(f"**{key}:** {value}")

        # Optional preview
        with st.expander("📄 View Extracted Text"):
            st.text_area("Raw Text", text[:3000], height=250)

        # Download
        output = "\n".join([f"{k}: {v}" for k, v in fields.items()])
        st.download_button(
            "💾 Download Extracted Info",
            data=io.BytesIO(output.encode()),
            file_name="statement_summary.txt",
            mime="text/plain"
        )

        st.success("✅ Extraction Complete")

    except Exception as e:
        st.error(f"❌ Error: {e}")

else:
    st.info("Upload a credit card statement PDF to begin.")
