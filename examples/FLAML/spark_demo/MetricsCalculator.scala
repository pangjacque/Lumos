package com.example

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

trait MetricCalculator {
  def calculate(df: DataFrame): Double
}

object MetricsCalculator extends MetricCalculator {
  def calculate(df: DataFrame): Double = {
    df.agg(avg("value")).first().getDouble(0)
  }

  def giniCoefficient(df: DataFrame, labelCol: String, predCol: String): Double = {
    // Compute Gini coefficient from labels and predictions
    val sorted = df.orderBy(predCol)
    val total = sorted.count()
    sorted.agg(sum(labelCol)).first().getDouble(0) / total
  }
}

case class ModelMetrics(gini: Double, ks: Double, psi: Double)

class ModelEvaluator(spark: SparkSession) {
  def evaluate(predictions: DataFrame): ModelMetrics = {
    ModelMetrics(
      gini = MetricsCalculator.giniCoefficient(predictions, "label", "prediction"),
      ks = 0.0,
      psi = 0.0
    )
  }
}
