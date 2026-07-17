import pandas as pd


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    total_rows = len(df)

    # 1. Null checks
    for col in df.columns:
        null_count = int(df[col].isnull().sum())

        if null_count > 0:
            results.append({
                "Rule": "NULL_CHECK",
                "Column": col,
                "Status": "FAILED",
                "Issue Count": null_count,
                "Description": f"{null_count} null values found in {col}"
            })

    # 2. Blank string checks
    for col in df.select_dtypes(include=["object"]).columns:
        blank_count = int((df[col].astype(str).str.strip() == "").sum())

        if blank_count > 0:
            results.append({
                "Rule": "BLANK_STRING_CHECK",
                "Column": col,
                "Status": "FAILED",
                "Issue Count": blank_count,
                "Description": f"{blank_count} blank values found in {col}"
            })

    # 3. Duplicate row check
    duplicate_count = int(df.duplicated().sum())

    if duplicate_count > 0:
        results.append({
            "Rule": "DUPLICATE_ROW_CHECK",
            "Column": "ALL_COLUMNS",
            "Status": "FAILED",
            "Issue Count": duplicate_count,
            "Description": f"{duplicate_count} duplicate rows found"
        })

    # 4. Constant column check
    for col in df.columns:
        if df[col].nunique(dropna=True) == 1 and total_rows > 1:
            results.append({
                "Rule": "CONSTANT_COLUMN_CHECK",
                "Column": col,
                "Status": "WARNING",
                "Issue Count": total_rows,
                "Description": f"{col} has only one unique value"
            })

    if not results:
        results.append({
            "Rule": "BASIC_QUALITY_CHECK",
            "Column": "ALL_COLUMNS",
            "Status": "PASSED",
            "Issue Count": 0,
            "Description": "No basic data quality issues found"
        })

    return pd.DataFrame(results)