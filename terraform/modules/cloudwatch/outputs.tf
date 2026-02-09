output "sns_topic_arn" {
  description = "CloudWatch 알람 SNS Topic ARN"
  value       = aws_sns_topic.cloudwatch_alarms.arn
}

output "sns_topic_name" {
  description = "CloudWatch 알람 SNS Topic 이름"
  value       = aws_sns_topic.cloudwatch_alarms.name
}

output "discord_alert_function_arn" {
  description = "Discord Alert Lambda 함수 ARN"
  value       = aws_lambda_function.discord_alert.arn
}

output "discord_alert_function_name" {
  description = "Discord Alert Lambda 함수 이름"
  value       = aws_lambda_function.discord_alert.function_name
}

output "dashboard_arn" {
  description = "CloudWatch Dashboard ARN"
  value       = aws_cloudwatch_dashboard.main.dashboard_arn
}

output "log_group_arns" {
  description = "Lambda 로그 그룹 ARN 목록"
  value = {
    for fn in var.lambda_function_names : fn => aws_cloudwatch_log_group.lambda_logs[fn].arn
  }
}

output "alarm_arns" {
  description = "생성된 알람 ARN 목록"
  value = {
    lambda_errors = {
      for fn in var.lambda_function_names : fn => aws_cloudwatch_metric_alarm.lambda_errors[fn].arn
    }
    lambda_duration = {
      for fn in var.lambda_function_names : fn => aws_cloudwatch_metric_alarm.lambda_duration[fn].arn
    }
    lambda_throttles = {
      for fn in var.lambda_function_names : fn => aws_cloudwatch_metric_alarm.lambda_throttles[fn].arn
    }
  }
}
