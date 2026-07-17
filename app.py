from charts import null_chart
from charts import datatype_chart
from dashboard import get_dashboard_metrics
from validator import validate_dataframe
from profiler import generate_profile
from ai_service import generate_ai_insights, AIServiceError, _ENV_PATH
from sql_engine import ask_dataset, SQLEngineError
import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="DATA🔎SHERLOCK",
    page_icon="🎩📊",
    layout="wide"
)

st.title("DATA🔎SHERLOCK")
st.caption("AI-powered Data Engineering Assistant")

with st.sidebar:
    st.subheader("⚙️ Settings")
    sidebar_api_key = st.text_input(
        "Gemini API Key",
        value="",
        type="password",
        help=(
            "Optional if GEMINI_API_KEY is already set in a .env file "
            "in the project root. Get a key at aistudio.google.com/apikey"
        ),
    )
    if os.environ.get("GEMINI_API_KEY") or sidebar_api_key:
        st.caption("✅ Gemini key detected")
    else:
        st.caption("⚠️ No Gemini key set yet")
        st.caption(f"Looking for .env at: `{_ENV_PATH}`")
        st.caption(f".env exists at that path: {_ENV_PATH.exists()}")

st.divider()

if "df" not in st.session_state:
    st.session_state.df = None

if "file_name" not in st.session_state:
    st.session_state.file_name = None

if "file_type" not in st.session_state:
    st.session_state.file_type = None

if "ai_insights" not in st.session_state:
    st.session_state.ai_insights = None

if "sql_result" not in st.session_state:
    st.session_state.sql_result = None

uploaded_file = st.file_uploader(
    "Upload CSV or TSV",
    type=["csv", "tsv"]
)

if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1].lower()

    if file_extension == "csv":
        st.session_state.df = pd.read_csv(uploaded_file)
    elif file_extension == "tsv":
        st.session_state.df = pd.read_csv(uploaded_file, sep="\t")

    if uploaded_file.name != st.session_state.file_name:
        st.session_state.ai_insights = None
        st.session_state.sql_result = None

    st.session_state.file_name = uploaded_file.name
    st.session_state.file_type = file_extension.upper()

if st.session_state.df is not None:
    df = st.session_state.df
    metrics = get_dashboard_metrics(df)
    profile = generate_profile(df)
    validation_results = validate_dataframe(df)
    st.success(f"Dataset Loaded Successfully: {st.session_state.file_name}")

    if st.button("Clear Uploaded Dataset"):
        st.session_state.df = None
        st.session_state.file_name = None
        st.session_state.file_type = None
        st.session_state.ai_insights = None
        st.session_state.sql_result = None
        st.rerun()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Rows", metrics["rows"])

    col2.metric("Columns", metrics["columns"])

    col3.metric("Null Cells", metrics["nulls"])

    col4.metric("Duplicate Rows", metrics["duplicates"])

    col5.metric(
        "Quality Score",
        f"{metrics['quality_score']}%"
    )

    st.divider()

    st.subheader("Dataset Preview")
    st.dataframe(df, use_container_width=True)

    st.divider()

    st.subheader("Column Statistics")
    profile = generate_profile(df)
    st.dataframe(profile, use_container_width=True)

    st.divider()

    st.subheader("Data Quality Validation")
    validation_results = validate_dataframe(df)
    st.dataframe(validation_results, use_container_width=True)

    st.divider()

    st.subheader("Visual Analytics")
    
    left, right = st.columns(2)
    
    with left:
        st.plotly_chart(
            null_chart(df),
            use_container_width=True
        )
    
    with right:
        st.plotly_chart(
            datatype_chart(df),
            use_container_width=True
        )

    st.divider()

    st.subheader("🤖 AI Insights")

    if st.button("Generate AI Insights", type="primary"):
        with st.spinner("Asking Gemini to review this dataset..."):
            try:
                insights = generate_ai_insights(
                    df=df,
                    metrics=metrics,
                    profile_df=profile,
                    validation_df=validation_results,
                    api_key=sidebar_api_key or None,
                )
                st.session_state.ai_insights = insights
            except AIServiceError as err:
                st.session_state.ai_insights = None
                st.error(str(err))

    insights = st.session_state.get("ai_insights")
    if insights:
        st.markdown("**Summary**")
        st.write(insights.summary)

        if insights.issues:
            st.markdown("**Issues**")
            for issue in insights.issues:
                st.markdown(f"- {issue}")

        if insights.recommendations:
            st.markdown("**Recommendations**")
            for rec in insights.recommendations:
                st.markdown(f"- {rec}")

    st.divider()

    st.subheader("💬 Ask Your Data")
    st.caption(
        "Ask a question in plain English. It's translated to SQL and "
        "run instantly against your dataset with DuckDB."
    )

    nl_query = st.text_input(
        "Your question",
        placeholder="e.g. What is the average fare by passenger class?",
        key="nl_query_input",
    )

    if st.button("Run Query", type="primary") and nl_query.strip():
        with st.spinner("Translating to SQL and running it..."):
            try:
                query_result = ask_dataset(
                    nl_query=nl_query,
                    df=df,
                    api_key=sidebar_api_key or None,
                )
                st.session_state.sql_result = query_result
            except SQLEngineError as err:
                st.session_state.sql_result = None
                st.error(str(err))

    sql_result = st.session_state.get("sql_result")
    if sql_result:
        st.code(sql_result.sql, language="sql")
        st.dataframe(sql_result.result, use_container_width=True)

else:
    st.info("Upload a CSV or TSV file to start profiling and validation.")