import random

import pandas as pd
import streamlit as st


st.set_page_config(page_title="LIMBO100k Dashboard", layout="wide")

st.title("LIMBO100k — Simulation Dashboard")
st.caption("Fictional probabilistic environment for bankroll and risk simulations.")


initial_capital = st.sidebar.number_input(
    "Initial capital",
    min_value=1.0,
    value=50.0,
    step=10.0,
)

iterations = st.sidebar.slider(
    "Iterations",
    min_value=10,
    max_value=500,
    value=100,
)

volatility = st.sidebar.slider(
    "Volatility",
    min_value=0.1,
    max_value=5.0,
    value=1.0,
)


capital = initial_capital
history = []

for step in range(iterations):
    variation = random.uniform(-1, 1) * volatility
    capital += variation
    capital = max(capital, 0)

    history.append(
        {
            "iteration": step + 1,
            "capital": round(capital, 2),
            "variation": round(variation, 2),
            "status": "positive" if variation >= 0 else "negative",
        }
    )


df = pd.DataFrame(history)

col1, col2, col3 = st.columns(3)

col1.metric("Final capital", f"{round(capital, 2)} €")
col2.metric("Positive outcomes", int((df['status'] == 'positive').sum()))
col3.metric("Negative outcomes", int((df['status'] == 'negative').sum()))

st.subheader("Capital evolution")
st.line_chart(df.set_index("iteration")["capital"])

st.subheader("Iteration history")
st.dataframe(df, use_container_width=True)
