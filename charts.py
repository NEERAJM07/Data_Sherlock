import pandas as pd
import plotly.express as px


def null_chart(df: pd.DataFrame):

    nulls = (
        df.isnull()
          .sum()
          .reset_index()
    )

    nulls.columns = ["Column", "Null Count"]

    fig = px.bar(
        nulls,
        x="Column",
        y="Null Count",
        title="Missing Values by Column"
    )

    return fig


def datatype_chart(df: pd.DataFrame):

    dtypes = (
        df.dtypes
        .astype(str)
        .value_counts()
        .reset_index()
    )

    dtypes.columns = ["Datatype", "Count"]

    fig = px.pie(
        dtypes,
        names="Datatype",
        values="Count",
        title="Column Datatypes"
    )

    return fig