import streamlit as st
import pandas as pd
from io import BytesIO

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Orders Aggregator", layout="wide")

# ------------------ HELPERS ------------------
def normalize_color(product_name):
    text = product_name.lower()

    if "blue" in text:
        return "Blue"
    if "black" in text:
        return "Black"
    if "brown" in text:
        return "Brown"

    return None  # unsupported color


def parse_inventory(df):
    df = df.copy()
    df["product_name"] = df["product_name"].astype(str)

    df["color"] = df["product_name"].apply(normalize_color)
    df["model"] = df["product_name"].apply(
        lambda x: " ".join(x.split()[:-1])
    )

    # remove rows with unsupported colors
    dropped = df[df["color"].isna()]
    if not dropped.empty:
        st.warning(
            f"⚠ {len(dropped)} products ignored due to unsupported colors"
        )

    df = df.dropna(subset=["color"])

    return df[["sku", "model", "color"]]



def aggregate_data(inventory_df, orders_df):
    merged = orders_df.merge(inventory_df, on="sku", how="left")

    if merged["model"].isna().any():
        st.warning("⚠ Some SKUs in orders file were not found in inventory.")

    pivot = pd.pivot_table(
        merged,
        index="model",
        columns="color",
        values="sku",
        aggfunc="count",
        fill_value=0
    )

    pivot["Total Orders"] = pivot.sum(axis=1)
    pivot.reset_index(inplace=True)

    return pivot


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

# ------------------ UI ------------------
st.title("📦 Orders Aggregator (XLSX → XLSX)")

inventory_file = st.file_uploader(
    "Upload Inventory Excel (.xlsx)",
    type=["xlsx"]
)

orders_file = st.file_uploader(
    "Upload Orders Excel (.xlsx)",
    type=["xlsx"]
)

if inventory_file and orders_file:
    inventory_df = pd.read_excel(inventory_file)
    orders_df = pd.read_excel(orders_file)

    required_inventory_cols = {"sku", "product_name"}
    required_orders_cols = {"sku"}

    if not required_inventory_cols.issubset(inventory_df.columns):
        st.error("Inventory file must contain columns: sku, product_name")
        st.stop()

    if not required_orders_cols.issubset(orders_df.columns):
        st.error("Orders file must contain column: sku")
        st.stop()

    parsed_inventory = parse_inventory(inventory_df)
    result_df = aggregate_data(parsed_inventory, orders_df)

    st.subheader("📊 Preview")
    st.dataframe(result_df)

    excel_file = to_excel(result_df)

    st.download_button(
        "⬇ Download Output Excel",
        excel_file,
        file_name="orders_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
