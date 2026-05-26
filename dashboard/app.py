import pandas as pd
import streamlit as st

from limbo100k.session_runner import run_fixed_strategy_session


st.set_page_config(page_title="LIMBO100k Dashboard", layout="wide")

st.title("LIMBO100k — Provably Fair Simulation")
st.caption("Deterministic fictional environment for bankroll and risk simulations.")


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
    "Stake per round",
    min_value=0.1,
    value=1.0,
    step=0.5,
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


summary = run_fixed_strategy_session(
    initial_capital=initial_capital,
    target_capital=target_capital,
    stake=stake,
    target_multiplier=multiplier,
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

    st.subheader("Round history")
    st.dataframe(df, use_container_width=True)

    st.subheader("Provably Fair commitment")
    st.code(df.iloc[0]["server_seed_hash"])
else:
    st.warning("No rounds were executed.")
