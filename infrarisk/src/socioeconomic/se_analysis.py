from pathlib import Path
from textwrap import wrap

import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import contextily as ctx

import os
import seaborn as sns

import matplotlib.pyplot as plt
import matplotlib.colors as colors
from mpl_toolkits.axes_grid1 import make_axes_locatable

import ipywidgets as widgets
from ipywidgets import fixed

CMAP = colors.LinearSegmentedColormap.from_list(
    "", ["green", "yellow", "orange", "red"]
)


class SocioEconomicTable:
    """A class for downloading and analyzing socioeconomic data for a given county in the United States. The module is used to quantify the sector-wise economic impacts from infrastructure disruptions."""

    def __init__(self, name, year, tract, state, county, dir):
        """Initialize the SocioEconomicTable class.

        :param name: Name of the county
        :type name: string
        :param year: Year of the data
        :type year: integer
        :param tract: Tract of the county
        :type tract: string
        :param state: State of the county
        :type state: string
        :param county: County of the county
        :type county: string
        :param dir: Directory to save the data
        :type dir: string
        """
        self.name = name
        self.year = year
        self.tract = tract
        self.state = state
        self.county = county
        self.dir = Path(dir)

        # Dictionary of 2-digit NAICS codes and their corresponding industry names
        self.industry_vars = {
            "DP03_0033E": "Agriculture, forestry, fishing and hunting, and mining",
            "DP03_0034E": "Construction",
            "DP03_0035E": "Manufacturing",
            "DP03_0036E": "Wholesale trade",
            "DP03_0037E": "Retail trade",
            "DP03_0038E": "Transportation and warehousing, and utilities",
            "DP03_0039E": "Information",
            "DP03_0040E": "Finance and insurance, and real estate and rental and leasing",
            "DP03_0041E": "Professional, scientific, and management, and \nadministrative and waste management services",
            "DP03_0042E": "Educational services, and health care and social assistance",
            "DP03_0043E": "Arts, entertainment, and recreation, and accommodation \nand food services",
            "DP03_0044E": "Other services, except public administration",
            "DP03_0045E": "Public administration",
        }

        # Dictionary of relevant variables in the County Business Patterns (CBP) dataset and their corresponding descriptions
        self.cbp_vars = {
            "NAME": "Geographic area code",
            # "EMP": "Number of employees",
            "ESTAB": "Number of establishments",
            "NAICS2017_LABEL": "2017 NAICS label",
            # "PAYANN": "Annual payroll ($1,000)",
            # "SECTOR": "NAICS economic sector",
            "ZIPCODE": "ZIP code",
        }

        # Dictionary of relevant variables in the Economic Census (ECN) dataset and their corresponding descriptions
        self.ecn_vars = {
            "NAME": "Geographic area code",
            "EMP": "Number of employees",
            "ESTAB": "Number of establishments",
            "NAICS2017_LABEL": "2017 NAICS label",
            "PAYANN": "Annual payroll ($1,000)",
            "SECTOR": "NAICS economic sector",
            "FIRM": "Number of firms",
            "OPEX": "Operating expenditures ($1,000)",
            "RCPTOT": "Sales, value of shipments, or revenue ($1,000)",
            "VALADD": "Value added ($1,000)",
            "TYPOP": "Type of operation",
            "YEAR": "Year",
        }

        # Dictionary of relevant variables in the American Business Survey (ACS) dataset and their corresponding descriptions
        self.abs_vars = {
            "EMP": "Number of employees",
            "FIRMPDEMP": "Number of employer firms",
            "NAICS2017_LABEL": "2017 NAICS label",
            "PAYANN": "Annual payroll ($1,000)",
            "RCPPDEMP": "Sales, value of shipments, or revenue of employer firms ($1,000)",
            "YEAR": "Year",
        }

        self.numeric_vars = [
            "EMP",
            "ESTAB",
            "PAYANN",
            "FIRM",
            "OPEX",
            "RCPTOT",
            "VALADD",
            "FIRMPDEMP",
            "RCPPDEMP",
        ]

        # Dictionary of 2-digit NAICS codes, their corresponding industry names, and resilience factors to infrastructure disruptions
        self.naics_codes = {
            "00": {
                "Industry": "Total for all industries",
                "P": None,
                "W": None,
                "PW": None,
            },
            "11": {
                "Industry": "Agriculture, Forestry, Fishing and Hunting",
                "P": 0.75,
                "W": 0.29,
                "PW": 0.75,
            },
            "21": {
                "Industry": "Mining, Quarrying, and Oil and Gas Extraction",
                "P": 0.25,
                "W": 1.0,
                "PW": 1.0,
            },
            "22": {"Industry": "Utilities", "P": 0.95, "W": 0.45, "PW": 0.97},
            "23": {"Industry": "Construction", "P": 0.71, "W": 0.31, "PW": 0.77},
            "31-33": {"Industry": "Manufacturing", "P": 0.95, "W": 0.45, "PW": 0.97},
            "42": {"Industry": "Wholesale Trade", "P": 0.79, "W": 0.42, "PW": 0.8},
            "44-45": {"Industry": "Retail Trade", "P": 0.79, "W": 0.42, "PW": 0.8},
            "48-49": {
                "Industry": "Transportation and Warehousing",
                "P": 0.73,
                "W": 0.23,
                "PW": 0.79,
            },
            "51": {"Industry": "Information", "P": 0.75, "W": 0.16, "PW": 0.81},
            "52": {
                "Industry": "Finance and Insurance",
                "P": 0.59,
                "W": 0.2,
                "PW": 0.69,
            },
            "53": {
                "Industry": "Real Estate and Rental and Leasing",
                "P": 0.56,
                "W": 0.4,
                "PW": 0.6,
            },
            "54": {
                "Industry": "Professional, Scientific, and Technical Services",
                "P": 0.74,
                "W": 0.22,
                "PW": 0.82,
            },
            "55": {
                "Industry": "Management of Companies and Enterprises",
                "P": 0.74,
                "W": 0.22,
                "PW": 0.82,
            },
            "56": {
                "Industry": "Administrative and Support and Waste Management and Remediation Services",
                "P": 0.74,
                "W": 0.22,
                "PW": 0.82,
            },
            "61": {
                "Industry": "Educational Services",
                "P": 0.74,
                "W": 0.22,
                "PW": 0.82,
            },
            "62": {
                "Industry": "Health Care and Social Assistance",
                "P": 0.68,
                "W": 0.48,
                "PW": 0.81,
            },
            "71": {
                "Industry": "Arts, Entertainment, and Recreation",
                "P": 0.75,
                "W": 0.25,
                "PW": 0.75,
            },
            "72": {
                "Industry": "Accommodation and Food Services",
                "P": 0.8,
                "W": 0.5,
                "PW": 0.85,
            },
            "81": {
                "Industry": "Other Services (except Public Administration)",
                "P": 0.74,
                "W": 0.22,
                "PW": 0.82,
            },
            "92": {
                "Industry": "Public Administration",
                "P": 0.75,
                "W": 0.25,
                "PW": 0.75,
            },
            "99": {
                "Industry": "Industries not classified",
                "P": None,
                "W": None,
                "PW": None,
            },
        }

        self.industry_to_naics_map = {
            "DP03_0033E": ["11", "21"],
            "DP03_0034E": ["23"],
            "DP03_0035E": ["31-33"],
            "DP03_0036E": ["42"],
            "DP03_0037E": ["44-45"],
            "DP03_0038E": ["22", "48-49"],
            "DP03_0039E": ["51"],
            "DP03_0040E": ["52", "53"],
            "DP03_0041E": ["54", "55", "56"],
            "DP03_0042E": ["61", "62"],
            "DP03_0043E": ["71", "72"],
            "DP03_0044E": ["81"],
            "DP03_0045E": ["92"],
        }

    def create_setable(self):
        """Create a socioeconomic table for the county zipcodes by combining American Business Survey data with County shapefile."""

        revenue_df = self.county_abs_df

        # expand county_gpd to include all naics
        total_naics_estabs = (
            self.county_cbp_df[["ESTAB", "NAICS2017", "ZIPCODE"]]
            .groupby(["ZIPCODE", "NAICS2017"])
            .sum()
            .reset_index()
        )
        total_naics_estabs = (
            total_naics_estabs.pivot(
                index="ZIPCODE", columns="NAICS2017", values="ESTAB"
            )
            .replace(0, np.nan)
            .fillna(0)
            .reset_index()
        )
        total_naics_estabs["ZIPCODE"] = total_naics_estabs["ZIPCODE"].astype(str)
        self.county_gpd_truncated["AREA_ID"] = self.county_gpd_truncated[
            "AREA_ID"
        ].astype(str)
        zip_revenue_df = self.county_gpd_truncated.merge(
            total_naics_estabs, left_on="AREA_ID", right_on="ZIPCODE"
        )

        industry_rcptot = {x: 0 for x in self.naics_codes.keys()}

        for _, row in revenue_df.iterrows():
            industry_rcptot[row["NAICS2017"]] += row["Total Revenue"]

        self.available_naics = {}
        for industry, values in self.naics_codes.items():
            industry_revenue = industry_rcptot[industry]
            if industry in zip_revenue_df.columns:
                if industry_revenue > 0:
                    self.available_naics[industry] = values
                zip_revenue_df[industry] = (
                    0.001
                    * industry_revenue
                    * zip_revenue_df["AREA_FRAC"]
                    * zip_revenue_df[industry]
                    / zip_revenue_df[industry].sum()
                )
        self.county_gpd_truncated = zip_revenue_df

    def download_zipcode_map(self, force_download=False):
        """Download zipcode shapefile from census.gov and save to the local drive.

        :param force_download: If True, download the zipcode-level county shapefile even if it already exists on the local drive.
        :type force_download: bool
        """
        if (
            not os.path.exists(
                self.dir / f"zipcode_{self.year}_{self.state}{self.county}.shp"
            )
            or force_download
        ):
            zip_url = f"https://www2.census.gov/geo/tiger/TIGER2010/ZCTA5/2010/tl_2010_{self.state}_zcta510.zip"
            print(f"Downloading {self.name} zipcode shapefile from {zip_url}...")
            zip_gpd = gpd.read_file(zip_url)

            county_url = f"https://www2.census.gov/geo/tiger/TIGER{self.year}/COUNTY/tl_{self.year}_us_county.zip"
            print(f"Downloading {self.name} county shapefile from {county_url}...")
            county_borders_gpd = gpd.read_file(county_url)
            county_borders_gpd = county_borders_gpd[
                county_borders_gpd["GEOID"] == str(self.state) + str(self.county)
            ]

            county_gpd_truncated = gpd.overlay(
                zip_gpd, county_borders_gpd, how="intersection"
            )
            county_gpd_truncated = county_gpd_truncated.to_crs({"init": "epsg:3857"})
            self.county_gpd_truncated = county_gpd_truncated[
                ["ZCTA5CE10", "GEOID10", "geometry"]
            ]
            self.county_gpd_truncated.columns = [
                "AREA_ID",
                "GEOID",
                "geometry",
            ]
            self.county_gpd_truncated["AREA"] = self.county_gpd_truncated[
                "geometry"
            ].area

            self.zip_codes = self.county_gpd_truncated["AREA_ID"].unique().tolist()

            county_gpd = zip_gpd[zip_gpd["ZCTA5CE10"].isin(self.zip_codes)]
            county_gpd = county_gpd[["ZCTA5CE10", "GEOID10", "geometry"]]

            self.county_gpd = county_gpd.to_crs({"init": "epsg:3857"}).reset_index(
                drop=True
            )
            self.county_gpd.columns = ["AREA_ID", "GEOID", "geometry"]
            self.county_gpd["AREA"] = self.county_gpd["geometry"].area

            self.county_gpd_truncated["AREA_FRAC"] = (
                self.county_gpd_truncated["AREA"] / self.county_gpd["AREA"]
            )
            self.county_gpd_truncated["AREA"] = self.county_gpd_truncated[
                "geometry"
            ].area
            self.county_gpd = None
            self.county_gpd_truncated["AREA_FRAC"] = self.county_gpd_truncated[
                "AREA_FRAC"
            ].round(2)

            self.county_gpd_truncated.to_file(
                self.dir / f"zipcode_{self.year}_{self.state}{self.county}.shp"
            )

        else:
            self.county_gpd_truncated = gpd.read_file(
                self.dir / f"zipcode_{self.year}_{self.state}{self.county}.shp"
            )

        xdiff = (
            self.county_gpd_truncated.bounds.maxx.max()
            - self.county_gpd_truncated.bounds.minx.min()
        )
        ydiff = (
            self.county_gpd_truncated.bounds.maxy.max()
            - self.county_gpd_truncated.bounds.miny.min()
        )

        tol = [0.1, 0.1]
        self.bounds = [
            self.county_gpd_truncated.bounds.minx.min() - tol[0] * xdiff,
            self.county_gpd_truncated.bounds.maxx.max() + tol[0] * xdiff,
            self.county_gpd_truncated.bounds.miny.min() - tol[1] * ydiff,
            self.county_gpd_truncated.bounds.maxy.max() + tol[1] * ydiff,
        ]

    def download_acs5_data(self, force_download=False):
        """Download 5-year American Community Survey data from census.gov and save to the local drive.

        :param force_download: If True, download the ACS5 data even if it already exists on the local drive.
        :type force_download: bool
        """

        if (
            not os.path.exists(
                self.dir / f"acs5_{self.year}_{self.state}{self.county}.csv"
            )
            or force_download
        ):
            variables = ",".join(list(self.industry_vars.keys()))
            census_data_url = f"https://api.census.gov/data/{self.year}/acs/acs5/profile?get={variables}&for=tract:{self.tract}&in=state:{self.state}&in=county:{self.county}"
            print(f"Downloading ACS5 data from {census_data_url}...")
            r_data = requests.get(census_data_url)
            json = r_data.json()

            county_acs5_df = pd.DataFrame(json)
            county_acs5_df.columns = county_acs5_df.iloc[0]
            county_acs5_df = county_acs5_df.drop(0)

            for variable in self.industry_vars.keys():
                county_acs5_df[variable] = county_acs5_df[variable].astype("int")
            for column in county_acs5_df:
                if column in self.numeric_vars:
                    county_acs5_df[column] = county_acs5_df[column].astype("float")
            self.county_acs5_df = county_acs5_df
            self.county_acs5_df.to_csv(
                self.dir / f"acs5_{self.year}_{self.state}{self.county}.csv",
                index=False,
            )
        else:
            self.county_acs5_df = pd.read_csv(
                self.dir / f"acs5_{self.year}_{self.state}{self.county}.csv"
            )

    def download_cbp_data(self, force_download=False):
        """Download County Business Patterns data from census.gov and save to the local drive.

        :param force_download: If True, download the CBP data even if it already exists on the local drive.
        :type force_download: bool
        """

        if (
            not os.path.exists(
                self.dir / f"cbp_{self.year}_{self.state}{self.county}.csv"
            )
            or force_download
        ):
            variables = ",".join(list(self.cbp_vars.keys()))
            zip_codes = ",".join(self.zip_codes)
            census_data_url = f"https://api.census.gov/data/2020/cbp?get={variables}&for=zip%20code:{zip_codes}&NAICS2017=*&LFO=001&EMPSZES=001"

            print(f"Downloading CBP data from {census_data_url}...")
            r_data = requests.get(census_data_url)
            json = r_data.json()

            county_cbp_df = pd.DataFrame(json)
            county_cbp_df.columns = county_cbp_df.iloc[0]
            county_cbp_df = county_cbp_df[
                county_cbp_df["NAICS2017"]
                .astype("str")
                .isin(list(self.naics_codes.keys()))
            ].reset_index(drop=True)

            for column in county_cbp_df:
                if column in self.numeric_vars:
                    county_cbp_df[column] = county_cbp_df[column].astype("float")
            county_cbp_df = county_cbp_df.drop(0)

            self.county_cbp_df = county_cbp_df
            self.county_cbp_df.to_csv(
                self.dir / f"cbp_{self.year}_{self.state}{self.county}.csv", index=False
            )
        else:
            self.county_cbp_df = pd.read_csv(
                self.dir / f"cbp_{self.year}_{self.state}{self.county}.csv"
            )

    def download_ecnbasic_data(self, force_download=False):
        """Download Economic Census Basic data from census.gov and save to the local drive.

        :param force_download: If True, download the ECNBasic data even if it already exists on the local drive.
        :type force_download: bool
        """

        if (
            not os.path.exists(
                self.dir / f"ecn_{self.year}_{self.state}{self.county}.csv"
            )
            or force_download
        ):
            variables = ",".join(list(self.ecn_vars.keys()))
            census_data_url = f"https://api.census.gov/data/2017/ecnbasic?get={variables}&for=county:{self.county}&in=state:{self.state}&NAICS2017=*"
            print(f"Downloading ECN data from {census_data_url}...")
            r_data = requests.get(census_data_url)
            json = r_data.json()

            county_ecn_df = pd.DataFrame(json)
            county_ecn_df.columns = county_ecn_df.iloc[0]
            county_ecn_df = county_ecn_df[
                county_ecn_df["NAICS2017"]
                .astype("str")
                .isin(list(self.naics_codes.keys()))
            ].reset_index(drop=True)
            county_ecn_df = county_ecn_df.drop(0)

            for column in county_ecn_df:
                if column in self.numeric_vars:
                    county_ecn_df[column] = county_ecn_df[column].astype("float")
            county_ecn_df["Total Revenue"] = county_ecn_df["RCPTOT"]

            self.county_ecn_df = county_ecn_df
            self.county_ecn_df.to_csv(
                self.dir / f"ecn_{self.year}_{self.state}{self.county}.csv", index=False
            )
        else:
            self.county_ecn_df = pd.read_csv(
                self.dir / f"ecn_{self.year}_{self.state}{self.county}.csv"
            )

    def download_abs_data(self, force_download=False):
        """Download Annual Business Survey data from census.gov and save to the local drive.

        :param force_download: If True, download the ABS data even if it already exists on the local drive.
        :type force_download: bool
        """

        if (
            not os.path.exists(
                self.dir / f"abs_{self.year}_{self.state}{self.county}.csv"
            )
            or force_download
        ):
            variables = ",".join(list(self.abs_vars.keys()))
            census_data_url = f"https://api.census.gov/data/{self.year}/abscs?get={variables}&for=county:{self.county}&in=state:{self.state}&NAICS2017=*"
            print(f"Downloading ABS data from {census_data_url}...")
            r_data = requests.get(census_data_url)
            json = r_data.json()

            county_abs_df = pd.DataFrame(json)
            county_abs_df.columns = county_abs_df.iloc[0]
            # county_abs_df = county_abs_df[
            #     county_abs_df["NAICS2017"].astype("str").isin(list(self.naics_codes.keys()))
            # ].reset_index(drop=True)
            county_abs_df = county_abs_df.drop(0)

            for column in county_abs_df:
                if column in self.numeric_vars:
                    county_abs_df[column] = county_abs_df[column].astype("float")
            county_abs_df["Total Revenue"] = county_abs_df["RCPPDEMP"]

            self.county_abs_df = county_abs_df
            self.county_abs_df.to_csv(
                self.dir / f"abs_{self.year}_{self.state}{self.county}.csv", index=False
            )
        else:
            self.county_abs_df = pd.read_csv(
                self.dir / f"abs_{self.year}_{self.state}{self.county}.csv"
            )

    def load_se_data(self):
        self.county_gpd_truncated = gpd.read_file(
            self.dir / f"zipcode_{self.year}_{self.state}{self.county}.shp"
        )
        xdiff = (
            self.county_gpd_truncated.bounds.maxx.max()
            - self.county_gpd_truncated.bounds.minx.min()
        )
        ydiff = (
            self.county_gpd_truncated.bounds.maxy.max()
            - self.county_gpd_truncated.bounds.miny.min()
        )
        tol = [0.1, 0.1]
        self.bounds = [
            self.county_gpd_truncated.bounds.minx.min() - tol[0] * xdiff,
            self.county_gpd_truncated.bounds.maxx.max() + tol[0] * xdiff,
            self.county_gpd_truncated.bounds.miny.min() - tol[1] * ydiff,
            self.county_gpd_truncated.bounds.maxy.max() + tol[1] * ydiff,
        ]

        self.county_cbp_df = pd.read_csv(
            self.dir / f"cbp_{self.year}_{self.state}{self.county}.csv"
        )

        self.county_ecn_df = pd.read_csv(
            self.dir / f"ecn_{self.year}_{self.state}{self.county}.csv"
        )
        self.county_abs_df = pd.read_csv(
            self.dir / f"abs_{self.year}_{self.state}{self.county}.csv"
        )

    def download_se_data(self, force_download=False):
        """Download all SE data (County maps, CBP, ECN and ABS datasets) from census.gov and save to the local drive.

        :param force_download: If True, download the SE data even if it already exists on the local drive.
        :type force_download: bool
        """

        self.download_zipcode_map(force_download=force_download)
        # self.download_acs5_data(force_download=force_download)
        self.download_cbp_data(force_download=force_download)
        self.download_ecnbasic_data(force_download=force_download)
        self.download_abs_data(force_download=force_download)

    def combine_infrastructure_se_data(self, integrated_network, resilience_metrics):
        """Combine the SE data with the infrastructure data.

        :param integrated_network: The integrated network object.
        :type integrated_network: infrarisk.src.physical.integrated_network.IntegratedNetwork
        :param resilience_metrics: The resilience metrics object.
        :type resilience_metrics: infrarisk.src.resilience_metrics.WeightedResilienceMetric
        """

        county_gpd_truncated = self.county_gpd_truncated.copy()

        water_sa = integrated_network.wn.service_area
        power_sa = integrated_network.pn.service_area

        zipcode_sa = gpd.overlay(
            county_gpd_truncated, water_sa, how="intersection"
        ).reset_index(drop=True)
        zipcode_sa = gpd.overlay(zipcode_sa, power_sa, how="intersection").reset_index(
            drop=True
        )
        zipcode_sa["AREA_FRAC"] = zipcode_sa.geometry.area / zipcode_sa["AREA"]

        zipcode_sa["power_EOH"] = zipcode_sa["Power_Node"].map(
            resilience_metrics.power_node_pcs_dict
        )
        zipcode_sa["water_EOH"] = zipcode_sa["Water_Node"].map(
            resilience_metrics.water_node_pcs_dict
        )
        self.zipcode_sa = zipcode_sa

    def calculate_economic_costs(self):
        """Calculate the zipcode-level economic costs of water and power outages for each industrial sector in the county."""

        economic_cost_df = self.zipcode_sa.copy()

        for industry in self.available_naics:
            if industry != "00":
                water_multiplier = self.naics_codes[industry]["W"]
                power_multiplier = self.naics_codes[industry]["P"]
                economic_cost_df[industry] = (
                    1000
                    * (1 / (365 * 24))
                    * (
                        water_multiplier * economic_cost_df["water_EOH"]
                        + power_multiplier * economic_cost_df["power_EOH"]
                    )
                    * economic_cost_df["AREA_FRAC"]
                    * economic_cost_df[industry]
                )
        unique_industry_list = list(self.available_naics.keys())
        unique_industry_list.remove("00")
        economic_cost_df["00"] = economic_cost_df[unique_industry_list].sum(axis=1)

        self.economic_cost_df = economic_cost_df.dissolve(
            "ZIPCODE", aggfunc="sum"
        ).reset_index()

    def plot_interactive(self, type="annual receipts"):
        """Plot the economic costs of water and power outages for each industrial sector in the county.

        :param type: The type of plot to generate. Options are "annual receipts" and "economic costs".
        :type type: string
        """

        if type == "annual receipts":
            widgets.interact(
                self.plot_industry_output,
                var=widgets.Dropdown(
                    description="Industry",
                    tooltip="Select an industry to plot",
                    options=sorted(
                        [value["Industry"] for _, value in self.available_naics.items()]
                    ),  # sorted(self.available_naics.values()),
                    value=sorted(
                        [value["Industry"] for _, value in self.available_naics.items()]
                    )[
                        0
                    ],  # list(self.available_naics.values())[0],
                    layout={"width": "max-content"},
                ),
                alpha=widgets.FloatSlider(
                    description="Transparency", value=0.8, min=0.2, max=1.0, step=0.1
                ),
                county_gpd_truncated=fixed(self.county_gpd_truncated),
            )
            # display(n_widget)

        elif type == "economic costs":
            widgets.interact(
                self.plot_economic_costs,
                var=widgets.Dropdown(
                    description="Industry",
                    tooltip="Select an industry to plot",
                    options=sorted(
                        [value["Industry"] for _, value in self.available_naics.items()]
                    ),  # sorted(self.available_naics.values()),
                    value=sorted(
                        [value["Industry"] for _, value in self.available_naics.items()]
                    )[
                        0
                    ],  # list(self.available_naics.values())[0],
                    layout={"width": "max-content"},
                ),
                alpha=widgets.FloatSlider(
                    description="Transparency", value=0.8, min=0.2, max=1.0, step=0.1
                ),
                # county_gpd_truncated=fixed(self.county_gpd_truncated),
                economic_cost_df=fixed(self.economic_cost_df),
            )
            # display(n_widget)

    def plot_industry_output(self, var, alpha):
        """Plot the annual receipts of an industry in the county.

        :param var: The name of the industry to plot.
        :type var: str
        :param alpha: The transparency of the plot.
        :type alpha: float
        """

        label = "Annual receipts in million US$"
        sns.set_context("talk", rc={"font.size": 20, "axes.titlesize": 20})
        sns.set_style("white")
        fig, axes = plt.subplots(
            1,
            2,
            figsize=(20, 10),
            gridspec_kw={"width_ratios": [3, 1.5]},
        )
        title = "\n".join(wrap(var + f" ({self.year})", 60))  # industry_vars[var]
        axes[0].set_title(title)
        axes[0].tick_params(labelsize=20)

        naics_list = [value["Industry"] for _, value in self.naics_codes.items()]
        var_name = list(self.naics_codes.keys())[naics_list.index(var)]

        # Plot the spatial map
        divider = make_axes_locatable(axes[0])
        cax = divider.append_axes("bottom", size="5%", pad=0.2)
        plot = self.county_gpd_truncated.plot(
            ax=axes[0],
            column=var_name,
            cmap=CMAP,
            edgecolor="black",
            linewidth=0.1,
            alpha=alpha,
            legend_kwds={
                "shrink": 0.25,
                "label": label,
                "orientation": "horizontal",
            },
            aspect=1,
            legend=True,
            cax=cax,
            vmin=0,
        )
        axes[0].set_xlim(self.bounds[0], self.bounds[1])
        axes[0].set_ylim(self.bounds[2], self.bounds[3])
        axes[0].axis("off")
        # ctx.add_basemap(ax=axes[0], source=ctx.providers.Stamen.Terrain)

        # Plot the histogram
        axes[1].set_title(title)
        histplot = sns.histplot(
            data=self.county_gpd_truncated,
            x=var_name,
            # binwidth=1000,
            color="steelblue",
            alpha=0.75,
            ax=axes[1],
        )
        histplot.set_xlabel(label)
        histplot.set_ylabel("Number of ZIP code tabulation areas")
        fig.tight_layout()
        fig.savefig("output.png", dpi=300, transparent=True)
        plt.show()

    def plot_economic_costs(self, var, alpha):
        """Plot the economic costs of an industry in the county.

        :param var: The name of the industry to plot.
        :type var: str
        :param alpha: The transparency of the plot.
        :type alpha: float
        """
        label = "Direct business disruption costs in (1000) US$"
        sns.set_context("talk", font_scale=1.1)
        sns.set_style("white")
        fig, axes = plt.subplots(
            1,
            2,
            figsize=(20, 10),
            gridspec_kw={"width_ratios": [3, 1.5]},
        )
        title = "\n".join(wrap(var + f" ({self.year})", 60))
        axes[0].set_title(title)

        naics_list = [value["Industry"] for _, value in self.naics_codes.items()]
        var_name = list(self.naics_codes.keys())[naics_list.index(var)]

        # Plot the spatial map
        divider = make_axes_locatable(axes[0])
        cax = divider.append_axes("bottom", size="5%", pad=0.2)
        plot = self.economic_cost_df.plot(
            ax=axes[0],
            column=var_name,
            cmap=CMAP,
            edgecolor="black",
            linewidth=0.1,
            alpha=alpha,
            legend_kwds={
                "shrink": 0.25,
                "label": label,
                "orientation": "horizontal",
            },
            aspect=1,
            legend=True,
            cax=cax,
            vmin=0,
            # vmax=1100,
        )
        axes[0].set_xlim(self.bounds[0], self.bounds[1])
        axes[0].set_ylim(self.bounds[2], self.bounds[3])
        axes[0].axis("off")
        ctx.add_basemap(ax=axes[0], source=ctx.providers.Stamen.Terrain)

        # Plot the histogram
        # axes[1].set_title(title)
        histplot = sns.histplot(
            data=self.economic_cost_df,
            x=var_name,
            color="steelblue",
            alpha=0.75,
            ax=axes[1],
            bins=10,
        )
        histplot.set_xlabel(label)
        histplot.set_ylabel("Number of ZIP code tabulation areas")
        fig.tight_layout()
        plt.show()
