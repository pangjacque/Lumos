"""Python wrapper that delegates heavy computation to Scala via Py4J.

This pattern is common in PySpark projects where Scala is used for
performance-critical operations (UDFs, custom aggregators, optimized joins)
and Python provides the orchestration layer.
"""

from pyspark.sql import SparkSession, DataFrame


class FeatureEngineerWrapper:
    """Python wrapper around the Scala FeatureEngineer class.

    All heavy DataFrame operations are delegated to the JVM-side Scala
    implementation for performance.
    """

    def __init__(self, spark: SparkSession):
        self.spark = spark
        # Bridge into the Scala implementation
        self._scala_obj = spark._jvm.com.example.MetricsCalculator()
        self._evaluator = spark._jvm.com.example.ModelEvaluator(spark._jsparkSession)

    def compute_metrics(self, df: DataFrame):
        """Compute all model metrics by delegating to Scala."""
        # Static method call into Scala
        return spark._jvm.com.example.MetricsCalculator.giniCoefficient(
            df._jdf, "label", "prediction"
        )

    def evaluate(self, predictions: DataFrame):
        """Evaluate model — delegates to Scala ModelEvaluator."""
        return self._evaluator.evaluate(predictions._jdf)

    def custom_metric(self):
        # Direct framework call (should be detected but marked as framework)
        rdd = self.spark.sparkContext._jvm.org.apache.spark.rdd.RDD
        return rdd
