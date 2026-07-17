import pandas as pd


def get_dashboard_metrics(df):

    total_rows = len(df)
    total_columns = len(df.columns)

    total_nulls = int(df.isnull().sum().sum())

    duplicate_rows = int(df.duplicated().sum())

    total_cells = total_rows * total_columns

    quality_score = round(
        ((total_cells - total_nulls) / total_cells) * 100,
        2
    )

    return {
        "rows": total_rows,
        "columns": total_columns,
        "nulls": total_nulls,
        "duplicates": duplicate_rows,
        "quality_score": quality_score
    }