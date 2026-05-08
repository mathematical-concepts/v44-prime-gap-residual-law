# A Three-Layer Empirical Residual Law for Consecutive Prime Gaps: Drift and Modular Resonance

This repository contains the official implementation, aggregated data, and the experimental audit engine described in the manuscript: *"A Three-Layer Empirical Residual Law for Consecutive Prime Gaps: Drift and Modular Resonance"*.

## Scope and Purpose

This repository is strictly intended to reproduce the empirical residual law for consecutive prime-gap pairs described in the paper.

**It is not intended as a primality testing tool, nor does it constitute a proof of any open conjecture (e.g., Riemann Hypothesis, Twin Prime Conjecture, Goldbach).** Our contribution is to empirically demonstrate that the residual structure of consecutive gaps is not adequately described as featureless noise. Instead, it contains a reproducible, causally testable component with a specific modular geometry that is even in $D$.

## Nomenclature & The Unified Parametric Equation

The baseline model used for residual calculation is **`V15_CAUSAL`**. The target metric is `resid_log`, defined as $\Delta = \log(H/W_0)$, evaluated strictly on out-of-sample forward blocks **`B07-B10`**.

For consecutive prime gaps $g_1 = p_{n+1} - p_n$ and $g_2 = p_{n+2} - p_{n+1}$, we define the spatial variables $S = g_1 + g_2$ and $D = g_2 - g_1$. The residual error $\Delta$ is parameterized by the scale variable $t = \log\log(p_{center})$.

The **Three-layer residual law** is defined by the model `V44_PRIMES_PREDICTOR_FROZEN` as:

$$\Delta(S,D;p) = E_0(S) + U(S,D;t) + R_{45}(S,D;t)$$

Where:
1. **`M0`** = $E_0(S)$: Static geometric envelope.
2. **`M3`** = $E_0(S) + U(S,D;t)$: Smooth scale-dependent drift (macroscopic expansion).
3. **`R45`** = $R_{45}(S,D;t)$: Modular resonance with wavelength $\Lambda=45$ in the $S,D$ coordinate representation.

## Reproducibility and Usage

### Installation
```bash
python -m venv .venv
```

#### Windows
```bash
.venv\Scripts\activate
```

#### Linux / macOS
```bash
source .venv/bin/activate
```

### Requirements
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Reproducibility check

From a fresh clone:

```bash
python -m py_compile src/v44_primes_predictor_frozen.py
python -m py_compile src/audit_v44b.py
python -m py_compile src/reproduce_figures.py
```



### Running the Frozen Predictor
The script `v44_primes_predictor_frozen.py` contains the frozen empirical parametric law.

**1. Display the mathematical formula:**
```bash
python src/v44_primes_predictor_frozen.py --show-formula
```

**2. Audit the Frozen Model:**
To verify the error reduction of the isolated Three-Layer equation (M0, M3, R45) on the provided sample data:
```bash
python src/audit_v44b.py
```

**3. Reproduce the Paper's Figures:**
To generate the high-resolution charts used in the Whitepaper, including the comparisons against historical controls (SmoothNested, Full2D, and Null/D-shuffle), the script uses the aggregated historical data provided in the `data/` folder:
```bash
python src/reproduce_figures.py
```

**4. Building the white paper**

```bash
cd paper
pdflatex whitepaper_three_layer_prime_gap_residual_law.tex
pdflatex whitepaper_three_layer_prime_gap_residual_law.tex
```


*Alternatively, you can explore the data interactively using the provided Jupyter Notebook: `notebooks/reproduce_main_figures.ipynb`.*

## Whitepaper

The draft white paper describing the empirical law, validation methods, and structural conjectures can be found in the repository root and the `paper/` directory:
* [WHITEPAPER.md](WHITEPAPER.md) (Markdown version)
* [paper/whitepaper_three_layer_prime_gap_residual_law.pdf](paper/whitepaper_three_layer_prime_gap_residual_law.pdf) (PDF)
* `paper/whitepaper_three_layer_prime_gap_residual_law.tex` (LaTeX source)

## Citation

If you use this repository, please cite the GitHub/Zenodo release. Citation metadata is provided in `CITATION.cff`.

## AI Assistance Disclosure

This repository contains code and analysis developed during an exploratory research process assisted by AI systems, including Gemini 3 and ChatGPT. AI tools were used for code prototyping, debugging, diagnostic design, interpretation support, and drafting assistance.

The author acknowledges the role of AI-assisted dialogue in accelerating the exploratory cycle of hypothesis generation, implementation, falsification, and refinement. All scripts, reported numerical results, mathematical formulations, and manuscript claims were reviewed and curated by the human author, who remains solely responsible for the repository contents.

## License
This project is licensed under the MIT License.