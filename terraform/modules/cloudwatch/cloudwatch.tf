# ============================================
# CloudWatch Log Groups for Lambda Functions
# ============================================

resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = toset(var.lambda_function_names)

  name              = "/aws/lambda/${each.value}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${each.value}-logs"
    Environment = var.environment
  }
}

# ============================================
# SNS Topic for CloudWatch Alarms
# ============================================

resource "aws_sns_topic" "cloudwatch_alarms" {
  name = "${var.project_name}-cloudwatch-alarms-${var.environment}"

  tags = {
    Name        = "${var.project_name}-alarms"
    Environment = var.environment
  }
}

# ============================================
# Discord Alert Lambda Function
# ============================================

data "archive_file" "discord_alert" {
  type        = "zip"
  source_file = "${path.module}/src/discord_alert.py"
  output_path = "${path.module}/builds/discord_alert.zip"
}

resource "aws_lambda_function" "discord_alert" {
  function_name = "${var.project_name}-discord-alert-${var.environment}"

  runtime     = "python3.10"
  handler     = "discord_alert.handler"
  role        = aws_iam_role.discord_alert_role.arn
  timeout     = 30
  memory_size = 128

  filename         = data.archive_file.discord_alert.output_path
  source_code_hash = data.archive_file.discord_alert.output_base64sha256

  environment {
    variables = {
      DISCORD_WEBHOOK_URL = var.discord_webhook_url
      ENVIRONMENT         = var.environment
      PROJECT_NAME        = var.project_name
    }
  }

  tags = {
    Name        = "${var.project_name}-discord-alert"
    Environment = var.environment
  }
}

# IAM Role for Discord Alert Lambda
resource "aws_iam_role" "discord_alert_role" {
  name = "${var.project_name}-discord-alert-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# CloudWatch Logs 권한 for Discord Alert Lambda
resource "aws_iam_role_policy" "discord_alert_logs" {
  name = "discord-alert-logs"
  role = aws_iam_role.discord_alert_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:*:*:*"
    }]
  })
}

# SNS Subscription: SNS → Discord Alert Lambda
resource "aws_sns_topic_subscription" "discord_alert" {
  topic_arn = aws_sns_topic.cloudwatch_alarms.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.discord_alert.arn
}

# Lambda permission for SNS to invoke
resource "aws_lambda_permission" "sns_invoke_discord_alert" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.discord_alert.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.cloudwatch_alarms.arn
}

# ============================================
# CloudWatch Alarms for Lambda Functions
# ============================================

# Lambda Error Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${each.value}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5분
  statistic           = "Sum"
  threshold           = var.alarm_thresholds.lambda_error_threshold
  alarm_description   = "Lambda 함수 ${each.value}에서 에러가 ${var.alarm_thresholds.lambda_error_threshold}회 이상 발생했습니다."
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]
  ok_actions    = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${each.value}-error-alarm"
    Environment = var.environment
  }
}

# Lambda Duration Alarms (느린 실행 감지)
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${each.value}-high-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_thresholds.lambda_duration_threshold_ms
  alarm_description   = "Lambda 함수 ${each.value}의 평균 실행 시간이 ${var.alarm_thresholds.lambda_duration_threshold_ms}ms를 초과했습니다."
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${each.value}-duration-alarm"
    Environment = var.environment
  }
}

# Lambda Throttles Alarm (동시 실행 제한 초과)
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${each.value}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Lambda 함수 ${each.value}에서 쓰로틀링이 발생했습니다."
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${each.value}-throttle-alarm"
    Environment = var.environment
  }
}

# ====================================
# CloudWatch Alarms for API Gateway 
# ====================================

# API Gateway 5XX Errors
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  count = var.api_gateway_id != "" ? 1 : 0

  alarm_name          = "${var.project_name}-api-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_thresholds.api_5xx_error_threshold
  alarm_description   = "API Gateway에서 5XX 에러가 ${var.alarm_thresholds.api_5xx_error_threshold}회 이상 발생했습니다."
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = var.api_gateway_id
    Stage = var.api_gateway_stage
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]
  ok_actions    = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${var.project_name}-api-5xx-alarm"
    Environment = var.environment
  }
}

# API Gateway 4XX Errors
resource "aws_cloudwatch_metric_alarm" "api_4xx_errors" {
  count = var.api_gateway_id != "" ? 1 : 0

  alarm_name          = "${var.project_name}-api-4xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_thresholds.api_4xx_error_threshold
  alarm_description   = "API Gateway에서 4XX 에러가 ${var.alarm_thresholds.api_4xx_error_threshold}회 이상 발생했습니다."
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = var.api_gateway_id
    Stage = var.api_gateway_stage
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${var.project_name}-api-4xx-alarm"
    Environment = var.environment
  }
}

# API Gateway Latency
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  count = var.api_gateway_id != "" ? 1 : 0

  alarm_name          = "${var.project_name}-api-high-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_thresholds.api_latency_threshold_ms
  alarm_description   = "API Gateway 평균 응답 시간이 ${var.alarm_thresholds.api_latency_threshold_ms}ms를 초과했습니다."
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = var.api_gateway_id
    Stage = var.api_gateway_stage
  }

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${var.project_name}-api-latency-alarm"
    Environment = var.environment
  }
}

# ============================================
# CloudWatch Dashboard
# ============================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = concat(
      # Lambda 호출 수 위젯
      [{
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Invocations"
          region = var.aws_region
          metrics = [
            for fn in var.lambda_function_names : ["AWS/Lambda", "Invocations", "FunctionName", fn]
          ]
          period = 300
          stat   = "Sum"
        }
      }],
      # Lambda 에러 위젯
      [{
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Errors"
          region = var.aws_region
          metrics = [
            for fn in var.lambda_function_names : ["AWS/Lambda", "Errors", "FunctionName", fn]
          ]
          period = 300
          stat   = "Sum"
        }
      }],
      # Lambda Duration 위젯
      [{
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Duration (ms)"
          region = var.aws_region
          metrics = [
            for fn in var.lambda_function_names : ["AWS/Lambda", "Duration", "FunctionName", fn]
          ]
          period = 300
          stat   = "Average"
        }
      }],
      # 알람 상태 위젯
      [{
        type   = "alarm"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "Alarm Status"
          alarms = concat(
            [for fn in var.lambda_function_names : aws_cloudwatch_metric_alarm.lambda_errors[fn].arn],
            [for fn in var.lambda_function_names : aws_cloudwatch_metric_alarm.lambda_duration[fn].arn]
          )
        }
      }]
    )
  })
}

# ============================================
# Log Metric Filters (에러 로그 감지)
# ============================================

resource "aws_cloudwatch_log_metric_filter" "lambda_error_logs" {
  for_each = toset(var.lambda_function_names)

  name           = "${each.value}-error-filter"
  pattern        = "?ERROR ?Error ?error ?Exception ?exception ?CRITICAL"
  log_group_name = aws_cloudwatch_log_group.lambda_logs[each.value].name

  metric_transformation {
    name      = "${each.value}-error-count"
    namespace = "${var.project_name}/CustomMetrics"
    value     = "1"
  }
}

# Custom metric alarm for log-based errors
resource "aws_cloudwatch_metric_alarm" "lambda_log_errors" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${each.value}-log-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "${each.value}-error-count"
  namespace           = "${var.project_name}/CustomMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Lambda 함수 ${each.value} 로그에서 에러 패턴이 3회 이상 감지되었습니다."
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.cloudwatch_alarms.arn]

  tags = {
    Name        = "${each.value}-log-error-alarm"
    Environment = var.environment
  }
}
