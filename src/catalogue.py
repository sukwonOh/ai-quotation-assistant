from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1] # Project root folder

# Product catalogue location

CATALOGUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "product_catalogue.csv"
)

REQUIRED_COLUMNS = [
    "product_id",
    "category",
    "product_name",
    "description",
    "unit",
    "material_price",
    "labour_price",
    "waste_factor",
    "gst_rate",
    "active",
]

def load_catelogue():
    """Load product catelogue from CSV."""
    if not CATALOGUE_PATH.exists():
        raise FileNotFoundError(
            f"Catalogue file not found: {CATALOGUE_PATH}"
        )

    df = pd.read_csv(CATALOGUE_PATH)

    return df

def validate_catalogue(df):
    """Check that the catalogue contains all required columns."""

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df["product_id"].duplicated().any():
        raise ValueError(
            "Duplicate product IDs found."
        )

    print("Catalogue validation successful✅")

def find_product_by_id(df, product_id):
    """Find a product using its product ID."""
    result = df[
        df["product_id"].str.upper()
        == product_id.upper()
    ]

    return result


def find_product_by_category(df, category):
    """Find product by category"""
    result = df[
        df["category"].str.strip().str.lower()
        == category.strip().lower()
    ]

    return result

def find_product_by_name(df, product_name):
    """ Find a product using its product name. Matching is case-insensitive. """

    result = df[
        df["product_name"].str.strip().str.casefold()
        == product_name.strip().casefold()
    ]

    return result

if __name__ == "__main__":
    catalogue = load_catelogue()

    validate_catalogue(catalogue)

    print("\nProduct catalogue:")
    print(catalogue)

    print("\nSearch example - CLD001:")
    print(
        find_product_by_id(
            catalogue,
            "CLD001"
        )
    )

    print("\nSearch example - Cladding:")
    print(
        find_product_by_category(
        catalogue,
        "Cladding"
        )
    )
