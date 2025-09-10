import streamlit as st
import pandas as pd
from nfl_picks_automator import update_picks  # Import your script function

st.title("NFL Picks Tracker")
uploaded_file = st.file_uploader("Upload your NFL Picks Excel", type=["xlsx", "xlsm"])
if uploaded_file:
    # Save uploaded file temporarily
    with open("temp_picks.xlsx", "wb") as f:
        f.write(uploaded_file.getvalue())
    
    # Run updater
    if st.button("Update with Latest Results"):
        try:
            update_picks(file_path="temp_picks.xlsx")
            st.success("Updated! Download the file below or view cumulative.")
            
            # Display Cumulative table
            cumulative_df = pd.read_excel("temp_picks.xlsx", sheet_name="Cumulative")
            st.table(cumulative_df)
            
            # Offer download
            with open("temp_picks.xlsx", "rb") as f:
                st.download_button("Download Updated Excel", f, file_name="updated_nfl_picks.xlsx")
        except Exception as e:
            st.error(f"Error updating file: {str(e)}\n\nPossible fix: Open your file in Excel, save as a new .xlsx (without macros/passwords), and upload that. If issues persist, the file may be corrupt—recreate it.")
    
    # Optional: Editable picks (advanced, but you can add data_editor for sheets)