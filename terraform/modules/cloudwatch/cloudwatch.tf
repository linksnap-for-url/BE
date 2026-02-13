# ============================================
# CloudWatch Log Groups
# ============================================

resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each          = toset(var.lambda_function_names)
  name              = "/aws/lambda/${each.value}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${each.value}-logs"
    Environment = var.environment
  }
}

# ============================================
# SNS Topic → Discord Alert Lambda
# ============================================

resource "aws_sns_topic" "cloudwatch_alarms" {
  name = "${var.project_name}-cloudwatch-alarms-${var.environment}"
  tags = { Name = "${var.project_name}-alarms", Environment = var.environment }
}

data "archive_file" "discord_alert" {
  type        = "zip"
  source_file = "${path.module}/src/discord_alert.py"
  output_path = "${path.module}/builds/discord_alert.zip"
}

resource "aws_lambda_function" "discord_alert" {
  function_name    = "${var.project_name}-discord-alert-${var.environment}"
  runtime          = "python3.10"
  handler          = "discord_alert.handler"
  role             = aws_iam_role.discord_alert_role.arn
  timeout          = 30
  memory_size      = 128
  filename         = data.archive_file.discord_alert.output_path
  source_code_hash = data.archive_file.discord_alert.output_base64sha256

  environment {
    variables = {
      DISCORD_WEBHOOK_URL = var.discord_webhook_url
      ENVIRONMENT         = var.environment
      PROJECT_NAME        = var.project_name
    }
  }

  tags = { Name = "${var.project_name}-discord-alert", Environment = var.environment }
}

resource "aws_iam_role" "discord_alert_role" {
  name = "${var.project_name}-discord-alert-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "discord_alert_logs" {
  name = "discord-alert-logs"
  role = aws_iam_role.discord_alert_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:*:*:*" }]
  })
}

resource "aws_sns_topic_subscription" "discord_alert" {
  topic_arn = aws_sns_topic.cloudwatch_alarms.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.discord_alert.arn
}

resource "aws_lambda_permission" "sns_invoke_discord_alert" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.discord_alert.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.cloudwatch_alarms.arn
}

# ============================================
# Lambda Alarms
# ============================================

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each            = toset(var.lambda_function_names)
  alarm_name          = "${each.value}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_thresholds.lambda_error_threshold
  alarm_description   = "Lambda ${each.value} error threshold exceeded"
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = each.value }
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  ok_actions          = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${each.value}-error-alarm", Environment = var.environment }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each            = toset(var.lambda_function_names)
  alarm_name          = "${each.value}-high-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_thresholds.lambda_duration_threshold_ms
  alarm_description   = "Lambda ${each.value} duration threshold exceeded"
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = each.value }
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${each.value}-duration-alarm", Environment = var.environment }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each            = toset(var.lambda_function_names)
  alarm_name          = "${each.value}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Lambda ${each.value} throttled"
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = each.value }
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${each.value}-throttle-alarm", Environment = var.environment }
}

# ============================================
# API Gateway Alarms
# ============================================

resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  count               = var.enable_api_gateway_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-api-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_thresholds.api_5xx_error_threshold
  alarm_description   = "API Gateway 5XX errors exceeded"
  treat_missing_data  = "notBreaching"
  dimensions          = { ApiId = var.api_gateway_id, Stage = var.api_gateway_stage }
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  ok_actions          = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${var.project_name}-api-5xx-alarm", Environment = var.environment }
}

resource "aws_cloudwatch_metric_alarm" "api_4xx_errors" {
  count               = var.enable_api_gateway_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-api-4xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_thresholds.api_4xx_error_threshold
  alarm_description   = "API Gateway 4XX errors exceeded"
  treat_missing_data  = "notBreaching"
  dimensions          = { ApiId = var.api_gateway_id, Stage = var.api_gateway_stage }
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${var.project_name}-api-4xx-alarm", Environment = var.environment }
}

resource "aws_cloudwatch_metric_alarm" "api_latency" {
  count               = var.enable_api_gateway_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-api-high-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_thresholds.api_latency_threshold_ms
  alarm_description   = "API Gateway latency exceeded"
  treat_missing_data  = "notBreaching"
  dimensions          = { ApiId = var.api_gateway_id, Stage = var.api_gateway_stage }
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${var.project_name}-api-latency-alarm", Environment = var.environment }
}

# ============================================
# CloudWatch Dashboard
# ============================================

locals {
  src_redir = "'/aws/lambda/${var.lambda_function_names[1]}'"

  # 함수 이름에서 짧은 라벨 생성 (url-shortener- 제거)
  fn_labels = { for fn in var.lambda_function_names : fn => replace(replace(fn, "url-shortener-", ""), "-dev", "") }
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = concat(
      # ── Row 0-9: 메트릭 위젯 ──
      [
        { type = "metric", x = 0, y = 0, width = 8, height = 6, properties = { title = "Lambda Invocations", region = var.aws_region, metrics = [for fn in var.lambda_function_names : ["AWS/Lambda", "Invocations", "FunctionName", fn]], period = 300, stat = "Sum", view = "timeSeries" } },
        { type = "metric", x = 8, y = 0, width = 8, height = 6, properties = { title = "Lambda Errors", region = var.aws_region, metrics = [for fn in var.lambda_function_names : ["AWS/Lambda", "Errors", "FunctionName", fn]], period = 300, stat = "Sum", view = "timeSeries" } },
        { type = "metric", x = 16, y = 0, width = 8, height = 6, properties = { title = "Lambda Duration (ms)", region = var.aws_region, metrics = [for fn in var.lambda_function_names : ["AWS/Lambda", "Duration", "FunctionName", fn]], period = 300, stat = "Average", view = "timeSeries" } },
        { type = "alarm", x = 0, y = 6, width = 12, height = 4, properties = { title = "Alarm Status", alarms = concat([for fn in var.lambda_function_names : aws_cloudwatch_metric_alarm.lambda_errors[fn].arn], [for fn in var.lambda_function_names : aws_cloudwatch_metric_alarm.lambda_duration[fn].arn]) } },
        { type = "metric", x = 12, y = 6, width = 12, height = 4, properties = { title = "Lambda Throttles", region = var.aws_region, metrics = [for fn in var.lambda_function_names : ["AWS/Lambda", "Throttles", "FunctionName", fn]], period = 300, stat = "Sum", view = "timeSeries" } },
      ],

      # ── Row 10-21: 함수별 에러 로그 (각 함수 1개 위젯) ──
      [for idx, fn in var.lambda_function_names : {
        type = "log", x = (idx % 2) * 12, y = 10 + floor(idx / 2) * 6, width = 12, height = 6
        properties = {
          title  = "Errors: ${local.fn_labels[fn]}"
          region = var.aws_region
          view   = "table"
          query  = "SOURCE '/aws/lambda/${fn}' | fields @timestamp, @logStream, @message | filter @message like /(?i)(error|exception|critical|failed|timeout)/ | sort @timestamp desc | limit 20"
        }
      }],

      # ── Row 22-37: 함수별 최근 로그 ──
      [for idx, fn in var.lambda_function_names : {
        type = "log", x = (idx % 2) * 12, y = 22 + floor(idx / 2) * 8, width = 12, height = 8
        properties = {
          title  = "Logs: ${local.fn_labels[fn]}"
          region = var.aws_region
          view   = "table"
          query  = "SOURCE '/aws/lambda/${fn}' | fields @timestamp, @message | sort @timestamp desc | limit 30"
        }
      }],

      # ── Row 38-45: 리다이렉트 상세 로그 ──
      [
        {
          type = "log", x = 0, y = 38, width = 12, height = 8
          properties = {
            title  = "Redirect Logs"
            region = var.aws_region
            view   = "table"
            query  = "SOURCE ${local.src_redir} | fields @timestamp, @message | filter @message like /301/ or @message like /Location/ | sort @timestamp desc | limit 30"
          }
        },
        {
          type = "log", x = 12, y = 38, width = 12, height = 8
          properties = {
            title  = "Stats Failure Logs"
            region = var.aws_region
            view   = "table"
            query  = "SOURCE ${local.src_redir} | fields @timestamp, @message | filter @message like /WARN/ or @message like /stats/ | sort @timestamp desc | limit 30"
          }
        },
      ],

      # ── Row 46-51: Cold Start + Execution Report (redirect 함수 기준) ──
      [
        {
          type = "log", x = 0, y = 46, width = 12, height = 6
          properties = {
            title  = "Cold Start Detection (redirect)"
            region = var.aws_region
            view   = "table"
            query  = "SOURCE ${local.src_redir} | fields @timestamp, @logStream, @initDuration, @duration, @memorySize, @maxMemoryUsed | filter ispresent(@initDuration) | sort @timestamp desc | limit 20"
          }
        },
        {
          type = "log", x = 12, y = 46, width = 12, height = 6
          properties = {
            title  = "Lambda Execution Report (redirect)"
            region = var.aws_region
            view   = "table"
            query  = "SOURCE ${local.src_redir} | fields @timestamp, @logStream, @duration, @billedDuration, @memorySize, @maxMemoryUsed | filter @message like /REPORT/ | sort @timestamp desc | limit 30"
          }
        },
      ]
    )
  })
}

# ============================================
# Log Metric Filters
# ============================================

resource "aws_cloudwatch_log_metric_filter" "lambda_error_logs" {
  for_each       = toset(var.lambda_function_names)
  name           = "${each.value}-error-filter"
  pattern        = "?ERROR ?Error ?error ?Exception ?exception ?CRITICAL"
  log_group_name = aws_cloudwatch_log_group.lambda_logs[each.value].name
  metric_transformation {
    name      = "${each.value}-error-count"
    namespace = "${var.project_name}/CustomMetrics"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_log_errors" {
  for_each            = toset(var.lambda_function_names)
  alarm_name          = "${each.value}-log-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "${each.value}-error-count"
  namespace           = "${var.project_name}/CustomMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Lambda ${each.value} log errors exceeded"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.cloudwatch_alarms.arn]
  tags                = { Name = "${each.value}-log-error-alarm", Environment = var.environment }
}
