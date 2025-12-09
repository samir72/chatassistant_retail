# Installation

## Stable release

To install chatassistant_retail, run this command in your terminal:

```sh
uv add chatassistant_retail
```

Or if you prefer to use `pip`:

```sh
pip install chatassistant_retail
```

## From source

The source files for chatassistant_retail can be downloaded from the [Github repo](https://github.com/samir72/chatassistant_retail).

You can either clone the public repository:

```sh
git clone git://github.com/samir72/chatassistant_retail
```

Or download the [tarball](https://github.com/samir72/chatassistant_retail/tarball/master):

```sh
curl -OJL https://github.com/samir72/chatassistant_retail/tarball/master
```

Once you have a copy of the source, you can install it with:

```sh
cd chatassistant_retail
uv pip install -e .
```

## Sample Data

As of version 0.1.1, sample data files are **included in the repository** (in the `data/` directory). You don't need to generate them manually unless you want custom data.

Files included:
- `data/products.json` - Product inventory (220 KB)
- `data/sales_history.json` - Transaction history (3.6 MB)
- `data/purchase_orders.json` - Sample POs (1.3 KB)

To regenerate with custom parameters:

```bash
python scripts/generate_sample_data.py
```

## HuggingFace Spaces Deployment Notes

If deploying to HuggingFace Spaces, note that the installation process differs:

**Local Development:**
```bash
pip install -e .
```

**HuggingFace Spaces:**
- Uses sys.path manipulation in `app.py` instead of formal installation
- Dependencies install from `requirements.txt` (no package self-installation)
- This is a workaround for HF Spaces' Docker build constraints

The application works identically in both environments.
