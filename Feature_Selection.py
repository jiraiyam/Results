import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
import re


class SimpleAdjustmentSystem:
    def __init__(self, db_name='random_adjustments.db'):
        """Initialize database connection"""
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        """Create table to store random values used"""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    random_value REAL,
                    operation TEXT,
                    timestamp DATETIME
                )
            ''')

    def generate_and_store_random(self):
        """Generate a random value and store it in database"""
        # Generate small random value (between 0.01 and 0.1)
        random_value = np.random.uniform(0.01, 0.1)
        # Randomly choose addition or subtraction
        operation = np.random.choice(['+', '-'])

        # Store in database
        with self.conn:
            self.conn.execute('''
                INSERT INTO adjustments (random_value, operation, timestamp)
                VALUES (?, ?, ?)
            ''', (random_value, operation, datetime.now().isoformat()))

        return random_value, operation

    def adjust_dataframe(self, df, selected_features):
        """Adjust selected features in dataframe with same random value"""
        # Create a copy of the dataframe
        adjusted_df = df.copy()

        # Generate and store random value
        random_value, operation = self.generate_and_store_random()

        # Adjust only selected features
        for col in selected_features:
            for idx in df.index:
                current_value = df.loc[idx, col]

                # Apply operation
                if operation == '+':
                    new_value = current_value + random_value
                else:
                    new_value = current_value - random_value

                # Ensure value stays between 0 and 1
                new_value = max(0, min(1, new_value))
                adjusted_df.loc[idx, col] = round(new_value, 5)

        return adjusted_df, random_value, operation

    def get_adjustment_history(self):
        """Get history of random values used"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM adjustments 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        return cursor.fetchall()

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    st.title("Feature Selection Adjustment System")

    # Initialize session state for the system
    if 'system' not in st.session_state:
        st.session_state.system = SimpleAdjustmentSystem()

    # File uploader
    uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx'])

    if uploaded_file is not None:
        try:
            # Read the Excel file
            feature_selection = pd.read_excel(uploaded_file, skiprows=1)

            # Identify the first column name
            first_column_name = feature_selection.columns[0]

            # Display original data
            st.subheader("Original Data")
            st.dataframe(feature_selection)

            # Identify bxxxx columns
            bxxxx_columns = [col for col in feature_selection.columns if str(col).startswith('b')]

            # Rename bxxxx columns
            if bxxxx_columns:
                st.subheader("Rename bXXXX Columns")

                # Create a form for renaming
                with st.form(key='rename_columns_form'):
                    new_column_names = {}

                    # Create input for each bxxxx column
                    for col in bxxxx_columns:
                        new_column_names[col] = st.text_input(
                            f"Rename '{col}' to:",
                            value=col,
                            key=f"rename_{col}"
                        )

                    # Submit button
                    submit_button = st.form_submit_button(label='Confirm Renames')

                # If form is submitted, rename columns
                if submit_button:
                    # Rename the columns
                    feature_selection = feature_selection.rename(columns=new_column_names)

                    # Show renamed columns
                    st.subheader("Renamed Columns")
                    for old_name, new_name in new_column_names.items():
                        st.write(f"{old_name} → {new_name}")

            # Feature selection
            st.subheader("Select Features to Adjust")

            # Exclude the first column from feature selection
            feature_columns = feature_selection.columns.drop(first_column_name).tolist()

            # Multi-select for features
            selected_features = st.multiselect(
                "Choose features to adjust",
                options=feature_columns,
                default=feature_columns
            )

            # Adjustment button
            if st.button("Apply Random Adjustment"):
                if not selected_features:
                    st.warning("Please select at least one feature to adjust")
                else:
                    # Perform adjustment
                    adjusted_data, random_value, operation = st.session_state.system.adjust_dataframe(
                        feature_selection,
                        selected_features
                    )

                    # Display adjusted data
                    st.subheader("Adjusted Data")
                    st.dataframe(adjusted_data)

                    # Show adjustment details
                    st.info(f"Adjustment applied: {operation}{random_value}")

                    # Save options
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Save as CSV"):
                            adjusted_data.to_csv('adjusted_data.csv', index=False)
                            st.success("File saved as adjusted_data.csv")

                    with col2:
                        if st.button("Save as Excel"):
                            adjusted_data.to_excel('adjusted_data.xlsx', index=False)
                            st.success("File saved as adjusted_data.xlsx")

            # Adjustment History
            st.subheader("Adjustment History")
            history = st.session_state.system.get_adjustment_history()
            history_df = pd.DataFrame(history, columns=['ID', 'Random Value', 'Operation', 'Timestamp'])
            st.dataframe(history_df)

        except Exception as e:
            st.error(f"An error occurred: {e}")

    # Cleanup on app close
    st.sidebar.button("Close Database Connection", on_click=lambda: st.session_state.system.close())


if __name__ == "__main__":
    main()