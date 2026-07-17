import pandas as pd

def generate_profile(df: pd.DataFrame) -> pd.DataFrame:
    profile = pd.DataFrame({
        "Column": df.columns,
        "Datatype": df.dtypes.astype(str).values,
        "Null Count": df.isnull().sum().values,
        "Null %": (df.isnull().mean() * 100).round(2).values,
        "Unique Values": df.nunique().values,
        "Duplicate Values": [
            df[col].duplicated().sum() for col in df.columns
        ]
    })

    return profile