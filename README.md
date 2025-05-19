# LANDO: Linked Age-Depth Modeling

[![DOI](https://zenodo.org/badge/432999664.svg)](https://zenodo.org/badge/latestdoi/432999664)

<div align="right">
  <img src='src/LANDO_Logo.jpg' align="right" height="120" />
</div>

## About the Project

**LANDO** integrates the most commonly used age-depth modeling software into a unified multi-language Jupyter Notebook interface powered by [SoS Notebook](https://github.com/vatlab/sos-notebook). It supports:

- [_Bacon_](https://github.com/Maarten14C/rbacon) (Blaauw and Christen, 2011)
- [_Bchron_](https://github.com/andrewcparnell/Bchron) (Haslett and Parnell, 2008; Parnell et al., 2008) 
- [_clam_](https://github.com/Maarten14C/clam) (Blaauw, 2010)  
- [_hamstr_](https://github.com/EarthSystemDiagnostics/hamstr) (Dolman, 2021)  
- [_Undatable_](https://github.com/bryanlougheed/undatable) (Lougheed and Obrochta, 2019)  

It also supports fuzzy changepoint detection via [Holloway et al. (2021)](https://doi.org/10.1016/j.envsoft.2021.104993) to test model agreement with lithological changes.

---

## 🚀 Quickstart with Docker

You can run **LANDO** with no setup beyond Docker itself.

### ⚙️ Prerequisites

- Install [Docker Desktop](https://www.docker.com)
- Allocate **at least 12 GB RAM** in Docker Desktop under:  
  `Settings > Resources > Memory`

---

### 🧪 Option 1: One-Line Launch (recommended)

Use the included startup script to launch the LANDO environment in one step:

```bash
./LANDO
```

> This script launches Jupyter, waits for it to start, and opens your browser.

---

### 🐳 Option 2: Manual Docker Run

You can also start the container manually:

```bash
docker pull gregpfalz/lando-age-depth
docker run -it -p 8888:8888 gregpfalz/lando-age-depth
```

Then go to [http://localhost:8888/lab/tree/LANDO.ipynb](http://localhost:8888/lab/tree/LANDO.ipynb) in your browser.

---

### 📁 Project Directory

If you cloned this repo, the `./LANDO` script is a symlink to `launch-lando.sh`. You can inspect or modify that script for advanced control.

---

## 🔧 Built-in Language Support

| Language | Version |
|----------|--------:|
| Python   | 3.11    |
| R        | 4.3.1   |
| Octave   | 8.3.0   |

_MATLAB support is not bundled due to licensing._

---

## 🛠 Functionality

LANDO enables age-depth modeling across single and multiple cores. Input data can be supplied via CSV or PostgreSQL. Outputs include calibrated chronologies and visualizations.

| Modeling System | Key Parameters |
|-----------------|----------------|
| Bacon           | `acc.shape`, `acc.mean`, `mem.strength`, `ssize` |
| clam            | `types_curve`, `smoothness_curve`, `poly_degree_curve` |
| hamstr          | `K_fine` |
| Undatable       | `xfactor`, `bootpc` |

Call `help()` in Python cells for function documentation, e.g. `help(age_sr_plot.PlotAgeSR.plot_graph)`.

---

## License

GNU GPLv3 – See `LICENSE.txt` for details.

---

## Contact

Gregor Pfalz – [Gregor.Pfalz@aon.com](mailto:Gregor.Pfalz@aon.com)  
Bluesky: [@ClimateCompathy](https://bsky.app/profile/climatecompathy.bsky.social)  
GitHub: [https://github.com/GPawi/LANDO](https://github.com/GPawi/LANDO)
