import pandas as pd
import streamlit as st

from limbo100k.analytics.monte_carlo import run_monte_carlo
from limbo100k.session_runner import run_strategy_session


st.set_page_config(page_title="LIMBO100k Dashboard", layout="wide")

st.title("LIMBO100k — Provably Fair Simulation")
st.caption("Deterministic fictional environment for bankroll and risk simulations.")

strategy = st.sidebar.selectbox(
    "Strategy",
    ["fixed", "percentage", "adaptive"],
)

initial_capital = st.sidebar.number_input(
    "Initial capital",
    min_value=1.0,
    value=50.0,
    step=10.0,
)

target_capital = st.sidebar.number_input(
    "Target capital",
    min_value=10.0,
    value=1000.0,
    step=50.0,
)

stake = st.sidebar.number_input(
    "Fixed stake",
    min_value=0.1,
    value=1.0,
    step=0.5,
)

risk_fraction = st.sidebar.slider(
    "Risk fraction",
    min_value=0.005,
    max_value=0.2,
    value=0.02,
)

multiplier = st.sidebar.slider(
    "Target multiplier",
    min_value=1.1,
    max_value=100.0,
    value=2.0,
)

rounds = st.sidebar.slider(
    "Maximum rounds",
    min_value=10,
    max_value=5000,
    value=250,
)

server_seed = st.sidebar.text_input(
    "Server seed",
    value="LIMBO100k_SERVER",
)

client_seed = st.sidebar.text_input(
    "Client seed",
    value="Mathis",
)

mc_sessions = st.sidebar.slider(
    "Monte-Carlo sessions",
    min_value=10,
    max_value=2000,
    value=250,
)


tab_single, tab_monte_carlo = st.tabs(["Single session", "Monte-Carlo"])

with tab_single:
    summary = run_strategy_session(
        strategy=strategy,
        initial_capital=initial_capital,
        target_capital=target_capital,
        stake=stake,
        target_multiplier=multiplier,
        risk_fraction=risk_fraction,
        max_rounds=rounds,
        server_seed=server_seed,
        client_seed=client_seed,
    )

    df = pd.DataFrame(summary.history)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Final capital", f"{summary.final_capital} €")
    col2.metric("Peak capital", f"{summary.peak_capital} €")
    col3.metric("Positive rounds", summary.positive_rounds)
    col4.metric("Negative rounds", summary.negative_rounds)

    if not df.empty:
        st.subheader("Capital evolution")
        st.line_chart(df.set_index("round")["capital"])

        st.subheader("Drawdown evolution")
        st.line_chart(df.set_index("round")["drawdown_from_peak"])

        st.subheader("Round history")
        st.dataframe(df, use_container_width=True)

        st.subheader("Provably Fair commitment")
        st.code(df.iloc[0]["server_seed_hash"])
    else:
        st.warning("No rounds were executed.")

with tab_monte_carlo:
    report = run_monte_carlo(
        sessions=mc_sessions,
        initial_capital=initial_capital,
        target_capital=target_capital,
        stake=stake,
        target_multiplier=multiplier,
        max_rounds=rounds,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Average final capital", f"{report.average_final_capital} €")
    col2.metric("Median final capital", f"{report.median_final_capital} €")
    col3.metric("Sessions", report.sessions)

    col4, col5, col6, col7 = st.columns(4)
    col4.metric("Success rate", f"{report.success_rate} %")
    col5.metric("Depletion rate", f"{report.depletion_rate} %")
    col6.metric("Best session", f"{report.best_session} €")
    col7.metric("Worst session", f"{report.worst_session} €")

    st.info(
        "Monte-Carlo uses different deterministic seed pairs per session. "
        "It is designed to evaluate risk, not to predict future outcomes."
    )
