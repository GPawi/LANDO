# LANDO: Linked Age-Depth Modeling

[![DOI](https://zenodo.org/badge/432999664.svg)](https://zenodo.org/badge/latestdoi/432999664)

<div align="right">
  <img src='src/LANDO_Logo.jpg' align="right" height="120" />
</div>

## About the Project

**LANDO** integrates the most commonly used age-depth modeling software in a multi-language Jupyter Notebook powered by [SoS Notebook](https://github.com/vatlab/sos-notebook). It supports the following modeling systems:

- [_Bacon_](https://github.com/Maarten14C/rbacon) (Blaauw and Christen, 2011)  
- [_Bchron_](https://github.com/andrewcparnell/Bchron) (Haslett and Parnell, 2008; Parnell et al., 2008)  
- [_clam_](https://github.com/Maarten14C/clam) (Blaauw, 2010)  
- [_hamstr_](https://github.com/EarthSystemDiagnostics/hamstr) (Dolman, 2021)  
- [_Undatable_](https://github.com/bryanlougheed/undatable) (Lougheed and Obrochta, 2019)  

LANDO also includes the fuzzy changepoint evaluation method from [Holloway et al. (2021)](https://doi.org/10.1016/j.envsoft.2021.104993) to assess how well modeled age-depth chronologies align with lithological changes from independent proxy records.

---

## Quickstart with Docker

You can run **LANDO** using Docker—no local installations or setup required.

### 📦 Step 1: Download the pre-built Docker image

The LANDO image is available on Docker Hub:

```bash
docker pull gregpfalz/lando-age-depth
```

> 📌 Docker Hub page: https://hub.docker.com/r/gregpfalz/lando-age-depth

### ▶️ Step 2: Start the container

```bash
docker run -it -p 8888:8888 gregpfalz/lando-age-depth
```

Then open [http://localhost:8888/lab/tree/LANDO.ipynb](http://localhost:8888/lab/tree/LANDO.ipynb) in your browser to launch the notebook.

---

## Built-in Language Support

Programming Language | Version  
:---- | ----: 
Python | 3.11  
R      | 4.3.1  
Octave | 8.3.0  

_MATLAB support is not bundled due to licensing._

---

## Functionality

LANDO enables modeling for single and multi-core age determinations. Users can load input data via file or PostgreSQL database. Outputs include modeled chronologies and diagnostic plots with support for evaluating changepoints using proxy data.

Modeling software | Key Parameters
:---------------- | ------------------
Bacon             | `acc.shape`, `acc.mean`, `mem.strength`, `mem.mean`, `ssize`
clam              | `types_curve`, `smoothness_curve`, `poly_degree_curve`
hamstr            | `K`
Undatable         | `xfactor`, `bootpc`

For documentation of specific functions, use `help()` in the Python cells (e.g., `help(age_sr_plot.PlotAgeSR.plot_graph)`).

---

## License

Distributed under the GNU GPLv3 License. See `LICENSE.txt` for details.

---

## Contact

Gregor Pfalz – [Gregor.Pfalz@aon.com](mailto:Gregor.Pfalz@aon.com)  
Bluesky: [@ClimateCompathy](https://bsky.app/profile/climatecompathy.bsky.social)  
Project repository: [https://github.com/GPawi/LANDO](https://github.com/GPawi/LANDO)
