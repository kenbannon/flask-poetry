from flask import Flask, render_template, url_for, request, session
import pandas as pd
import os
import numpy as np
import pandas as pd
import re
from matched_markets.methodology.common_classes import GeoAssignment
from matched_markets.methodology import geoeligibility
from matched_markets.methodology import tbrmmdata
from matched_markets.methodology import tbrmmdesignparameters
from matched_markets.methodology import tbrmmdiagnostics
from matched_markets.methodology import tbrmatchedmarkets
from matched_markets.methodology import tbrmmdesign
from matched_markets.methodology import utils

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'csv'} # Define allowed files
 
app = Flask(__name__)
 
# Configure upload file path flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "secret_key"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # upload file flask
        f = request.files.get('file')
        response_data_file_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            f.filename
        )
        session['response_data_file_path'] = response_data_file_path
        f.save(response_data_file_path)
        

        response_column = 'quotes'

        geo_level_time_series = pd.read_csv(
            session['response_data_file_path'],
            encoding='unicode_escape'
        )


        geo_level_time_series["date"] = pd.to_datetime(geo_level_time_series["date"])
        for colname in ["quotes"]:
            geo_level_time_series[colname] = pd.to_numeric(geo_level_time_series[colname])

        num_geos = geo_level_time_series["geo"].nunique()




        ## The minimum detectable iROAS is defined as the value of the true iROAS such
        ## that, given a confidence_level (input) % confidence level for a one-sided
        ## test, gives a power_level (input) % power if the true iROAS is equal to the
        ## minimum detectable iROAS.
        minimum_detectable_iROAS =  0.4424779#@param{type: "number"}
        #@markdown Use an average order value of 1 if the design is based on
        #@markdown sales/revenue or an actual average order value (e.g. $80) for a
        #@markdown design based on transactions/footfall/contracts.
        average_order_value =  1#@param{type: "number"}

        confidence_level = 0.95 #@param {type:"number"}
        power_level = 0.80 #@param {type:"number"}
        experiment_duration_in_weeks = 4 #@param {type:"integer"}

        #@markdown List the maximum budget for the experiment e.g. 300000
        experiment_budget =  300000#@param{type: "number"}
        #@markdown List any alternative budget which you would like to test separated
        #@markdown by a comma, e.g. 125000, 150000
        alternative_budget = "100000" #@param{type: "string"}
        additional_budget = [float(re.sub(r"\W+", "", x)) for x in
                            alternative_budget.split(',') if alternative_budget != ""]

        #@markdown List the days and time periods that you want to exclude separated by
        #@markdown a comma e.g. 2019/10/10, 2010/10/11, 2018/10/20-2018/11/20.
        #@markdown The format for time periods is "YYYY/MM/DD - YYYY/MM/DD",
        #@markdown where the two dates specify the start and end date for the period.
        #@markdown The format for day is "YYYY/MM/DD". Leave empty to
        #@markdown use all days/weeks.
        day_week_exclude = "" #@param {type: "string"}
        day_week_exclude = [] if day_week_exclude == "" else [
            re.sub(r"\s+", "", x) for x in day_week_exclude.split(",")
        ]
        ## Find all the days we should exclude from the analysis from the input
        periods_to_exclude = utils.find_days_to_exclude(day_week_exclude)
        days_exclude = utils.expand_time_windows(periods_to_exclude)

        ## Additional constraints which will be flagged in red if not met in
        ## the design

        # upper bound on the minimal detectable relative lift
        minimum_detectable_lift_in_response_metric = 0.1 * 100
        # lower bound on the baseline revenue covered by the treatment group
        minimum_revenue_covered_by_treatment = 0.05 * 100

        frequency = "D"
        if frequency == "D":
            n_test = experiment_duration_in_weeks * 7
            ## Use the most recent ~6 months
            n_pretest = 180
        elif frequency == "W":
            n_test = experiment_duration_in_weeks
            n_pretest = 26

        ## Other constraints/parameters which are hidden to the user

        ## Ratio of avg. control group response / avg. treatment group response must be
        ## between 1/(1+volume_ratio_tolerance) and 1+volume_ratio_tolerance
        volume_ratio_tolerance = np.inf
        ## Ratio of number of control geos / number treatment geos must be
        ## between 1/(1+geo_ratio_tolerance) and 1+geo_ratio_tolerance
        geo_ratio_tolerance = np.inf
        ## Constrain on the % of the treatment group response with respect to the
        ## overall response
        treatment_share_range = (0.0001, 0.9999)
        ## Minimum and maximum number of geos to include in the treatment group
        treatment_geos_range = (1, num_geos - 1)
        ## Minimum and maximum number of geos to include in the control group
        control_geos_range = (1, num_geos - 1)
        ## Maximum number of geos to include in the search
        n_geos_max = num_geos
        ## Maximum number of pretest timepoints to include in the time series for the
        ## purpose of estimating minimum detectable response 
        n_pretest_max = n_pretest
        ## Number of design to store during the exhaustive search
        n_designs = 3
        ## Maximum assumed treatment-control correlation to use for estimating the MDR
        rho_max = 0.995
        ## Minimum acceptable Pearson correlation between the treatment and control
        ## time series.
        min_corr = 0.8
        ## Inverse quantile of the f distribution parameter 'phi' used in the TBR
        ## preanalysis formula.
        flevel = 0.9

        budget_range = (0.1, experiment_budget)
        min_volume_ratio = 1/(1 + volume_ratio_tolerance)
        max_volume_ratio = 1 + volume_ratio_tolerance

        tbr_parameters = tbrmmdesignparameters.TBRMMDesignParameters(
            n_test=n_test,
            iroas=minimum_detectable_iROAS,
            volume_ratio_tolerance=volume_ratio_tolerance,
            geo_ratio_tolerance=geo_ratio_tolerance,
            treatment_share_range=treatment_share_range,
            budget_range=budget_range,
            treatment_geos_range=treatment_geos_range,
            control_geos_range=control_geos_range,
            n_geos_max=n_geos_max,
            n_pretest_max=n_pretest_max,
            n_designs=n_designs,
            sig_level=confidence_level,
            power_level=power_level,
            min_corr=min_corr,
            rho_max=rho_max,
            flevel=flevel)

        # remove dates that the user wants to exclude
        data_for_design = geo_level_time_series[~geo_level_time_series['date']
                                                .isin(days_exclude)].copy()
        tbrclass = tbrmmdata.TBRMMData(df=data_for_design,
                                    response_column=response_column)

        MMclass = tbrmatchedmarkets.TBRMatchedMarkets(data=tbrclass,
                                                    parameters=tbr_parameters)
        
        max_feasible_number_of_designs = 5 * 10 ** 5

        if MMclass.count_max_designs() < max_feasible_number_of_designs:
            matched_designs = MMclass.exhaustive_search()
        else:
            matched_designs = MMclass.greedy_search()

        if len(matched_designs) == 0:
            raise ValueError(f'{Fore.RED}It wasn\'t possible to find a design within ' +
                        f'the constraint in input or because all the designs, ' +
                        f'did not pass one among the AA test, structural break ' +
                        f'test, or minimum correlation of 0.8\n')

        matched_designs.sort(reverse=True)
        chosen_design = matched_designs[0]

        minimum_iroas_aov = minimum_detectable_iROAS / average_order_value
        minimum_detectable_impact = chosen_design.diag.estimate_required_impact(
            chosen_design.diag.corr)

        optimal_budget = minimum_detectable_impact / minimum_iroas_aov
        lower_budget = optimal_budget *  0.8
        upper_budget = optimal_budget * 1.2
        list_of_budgets = [lower_budget, optimal_budget, upper_budget
                        ] + additional_budget

        first_day = geo_level_time_series["date"].max() - pd.Timedelta(
            str(experiment_duration_in_weeks) + "W")
        most_recent_geo_level_time_series = geo_level_time_series[
            geo_level_time_series['date'] > first_day]

        total_response = most_recent_geo_level_time_series[response_column].sum()
        # total_spend = most_recent_geo_level_time_series["cost"].sum()
        chosen_design.treatment_geos = {x for x in chosen_design.treatment_geos}
        chosen_design.control_geos = {x for x in chosen_design.control_geos}
        designs = []
        for budget in list_of_budgets:
            baseline = most_recent_geo_level_time_series.loc[
            most_recent_geo_level_time_series["geo"].isin(chosen_design.treatment_geos
                                                        ), response_column].sum()
        # cost_in_experiment = most_recent_geo_level_time_series.loc[
        #     most_recent_geo_level_time_series["geo"].isin(chosen_design.treatment_geos
        #                                                  ), "cost"].sum()
        min_detectable_iroas = (
            average_order_value * minimum_detectable_impact / budget)
        min_detectable_lift = (minimum_detectable_impact * 100 / baseline)
        num_treatment_geos = len(chosen_design.treatment_geos)
        num_control_geos = len(chosen_design.control_geos)
        num_removed_geos = num_geos - num_treatment_geos - num_control_geos
        treat_control_removed = (f'{num_treatment_geos}  /  {num_control_geos}  / ' +
                                f'{num_removed_geos}')
        revenue_covered = 100 * baseline / total_response
        # proportion_cost_in_experiment = cost_in_experiment / total_spend
        # national_budget = utils.human_readable_number(
        #     budget / proportion_cost_in_experiment)
        designs.append({
            "Budget": utils.human_readable_number(budget),
            "Minimum detectable iROAS": f'{min_detectable_iroas:.3}',
            "Minimum detectable lift in response": f'{min_detectable_lift:.2f} %',
            "Treatment/control/excluded geos": treat_control_removed,
            "Revenue covered by treatment group": f'{revenue_covered:.2f} %',
            "Cost/baseline response": f'{(budget / baseline * 100):.2f} %'
            # "Cost if test budget is scaled nationally": national_budget
        })


        ## convert the table to a pd.DataFrame and select a subset of columns
        designs = pd.DataFrame(designs)
        designs.index.rename("Design", inplace=True)
        designs = designs[["Budget", "Minimum detectable iROAS",
                        "Minimum detectable lift in response",
                        "Treatment/control/excluded geos",
                        "Revenue covered by treatment group",
                        "Cost/baseline response"]]
        designs = designs.to_html()
                        
        return designs
    return render_template('index.html')

@app.route('/get_response')
def get_df():
    uploaded_df = pd.read_csv(
        session['response_data_file_path'],
        encoding='unicode_escape'
    ).to_json()
    return uploaded_df
    
