# Model Design Documentation: Automated XGBoost Regression

## 1. Data Profile
The model utilizes the **Houses** dataset (ID: 537) sourced from **OpenML**. This dataset is a standard benchmark for regression tasks, specifically focusing on the California housing market.

### 1.1 Data Origin and Context
The data is derived from the 1990 US Census. It provides information regarding the median house value and various demographic/geographical features for census block groups (the smallest geographical unit for which the Census Bureau publishes sample data).

### 1.2 Feature Schema
The dataset consists of 8 input features and 1 target variable:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **median_income** | Numerical | Median income for households within a block of houses (measured in tens of thousands of US Dollars). |
| **housing_median_age** | Numerical | Median age of a house within a block; a lower number is a newer building. |
| **total_rooms** | Numerical | Total number of rooms within a block. |
| **total_bedrooms** | Numerical | Total number of bedrooms within a block. |
| **population** | Numerical | Total number of people residing within a block. |
| **households** | Numerical | Total number of households (a group of people residing within a home unit) for a block. |
| **latitude** | Numerical | A measure of how far north a house is; a higher value is further north. |
| **longitude** | Numerical | A measure of how far west a house is; a higher value is further west. |
| **median_house_value** | **Target** | Median house value for households within a block (measured in US Dollars). |

---

## 2. Model Selection and Architecture

### 2.1 Why XGBoost?
The implementation specifically targets **XGBoost (eXtreme Gradient Boosting)**. XGBoost is chosen over other ensemble methods like standard Gradient Boosting Machines (GBM) or Random Forests for several reasons:

* **Computational Efficiency:** XGBoost utilizes a "Histogram-based" algorithm (`tree_method='hist'`) and parallel processing, making it significantly faster than traditional GBM.
* **Regularization:** Unlike standard GBM, XGBoost includes L1 and L2 regularization, which helps prevent overfitting on tabular data like the Houses dataset.
* **Handling Sparsity:** It has an innate ability to handle missing values through "Sparsity-aware Split Finding."
* **Flexibility:** As demonstrated in Section 4 of the notebook, XGBoost allows for custom objective functions (e.g., `logregobj`), enabling the designer to optimize for specific business logic beyond standard squared error.

### 2.2 Why not Random Forest or standard GBM?
* **Random Forest:** While robust, Random Forests often hit a performance ceiling on complex non-linear tabular data because they rely on bagging. XGBoost's boosting approach (learning from residuals) typically yields lower bias and higher accuracy.
* **Standard GBM:** Standard implementations often lack the advanced hardware acceleration and the variety of "Grow Policies" (like `lossguide`) that XGBoost provides, which are crucial for the low-latency requirements mentioned in the FLAML introduction.

### 2.3 Hyperparameter Optimization (AutoML)
The design leverages **FLAML** to automate the search for the optimal configuration. The primary hyperparameters tuned include:
* `n_estimators`: Number of boosting rounds.
* `max_leaves`: Complexity of the individual trees.
* `learning_rate`: The step size shrinkage to prevent overfitting.
* `subsample` and `colsample_bytree`: Stochastic parameters to improve generalization.

The implementation can be found in `flaml/automl/automl.py` using the `AutoML` class.
Training is executed in `notebook/automl_xgboost.ipynb`.

---

## 3. Evaluation and Metrics

### 3.1 Primary Metric: R-squared
The model's performance is primarily evaluated using the **Coefficient of Determination (R-squared)**.

The notebook achieves an R-squared of approximately **0.844**, indicating that 84.4% of the variance in house values is predictable from the features.

Metric calculation uses `sklearn_metric_loss_score()` from `flaml/ml.py`.

### 3.2 Secondary Metrics
To ensure a holistic view of error, the following are also tracked:
* **Mean Squared Error (MSE):** Useful for penalizing large outliers in price prediction.
* **Mean Absolute Error (MAE):** Provides an average "dollar amount" error that is more interpretable for stakeholders (found to be ~$30,303 in the default run).

### 3.3 Validation Strategy
The model uses **Cross-Validation (CV)** during the search phase and a final holdout test set for unbiased performance reporting. This ensures the tuned hyperparameters generalize well to unseen census blocks.

Results and analysis available in `notebook/automl_xgboost.ipynb`.

---

## 4. Potential Flaws and Improvement Roadmap

While the model is performant, the current design has several areas for optimization:

### 4.1 Feature Engineering (The "Rooms per Household" Gap)
* **Flaw:** The raw features `total_rooms` and `total_bedrooms` are highly dependent on the total population of the block.
* **Improvement:** Create derived features such as `rooms_per_household`, `population_per_household`, and `bedrooms_per_room`. These ratios are typically more indicative of house value than absolute counts.

### 4.2 Handling Logarithmic Scaling
* **Flaw:** Median house prices and incomes often follow a power-law distribution. The model currently predicts the raw value.
* **Improvement:** Applying a `log` transformation to the target variable (`median_house_value`) before training can stabilize variance and often leads to a better-performing model, especially when calculating MAPE (Mean Absolute Percentage Error).

### 4.3 Spatial Relationships
* **Flaw:** Latitude and longitude are treated as independent numerical features.
* **Improvement:** XGBoost cannot easily "see" that coordinates represent specific neighborhoods. Implementing **Spatial Clustering** (e.g., K-Means on coordinates) and using cluster IDs as a categorical feature could capture neighborhood-specific premiums.

### 4.4 Time Budget Constraints
* **Flaw:** The notebook log indicates that the hyperparameter search did not fully converge within the 120s budget.
* **Improvement:** Increase the `time_budget` or implement early stopping within the XGBoost parameters to allow for deeper exploration of the search space.

Data loading uses `load_openml_dataset()` from `flaml/automl/data.py`.
Training log analysis uses `get_output_from_log()` from `flaml/automl/data.py`.
